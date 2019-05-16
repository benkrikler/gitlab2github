#! /usr/bin/env python3

from collections import defaultdict
import gitlab
import github
import config
import re


def copy_milestones(gitlab_project, github_repo):
    """Copy milestones from gitlab to github.

    :param gitlab_project: the project id on gitlab
    :type gitlab_project: int
    :param github_repo: the project name on github
    :type github_repo: str
    """
    milestones_map = {}
    gitlab_milestones = gitlab_project.milestones.list()
    existing = github_repo.get_milestones()

    for milestone in gitlab_milestones:
        for exist in existing:
            if exist.title == milestone.title:
                milestones_map[milestone.id] = exist
                break
        else:
            github_milestone = dict(
                title=milestone.title, 
                description=milestone.description, 
                state='open' if milestone.state == 'active' else 'closed', 
            )
            if milestone.due_date:
                due_on=milestone.due_date
            github_milestone = github_repo.create_milestone(**github_milestone)
            if hasattr(github_milestone, "number"):
                milestones_map[milestone.id] = github_milestone
            else:
                print('Error copying milestone:\n{}'.format(github_milestone))
    return milestones_map


def _advise_manual_handling(github_comment, gitlab_note):
    
    if gitlab_note.attachment:
        print(
            "You must copy the attachment {} to {}".format(
                gitlab_note['attachment'], 
                github_comment.issue_url
            )
        )
#    urls = re.findall('{}/.+'.format(config.gitlab_url), gitlab_note['body'])
#    if urls:
#        print(
#            "The following urls on were internal to Gitlab, "
#            "you may want to change them at {}: \n{}".format(
#                github_url,    
#                '\n'.join(urls)
#            )
#        )



def copy_issue_comments(gitlab_issue, github_issue, gitlab_project, issues_map):
    """
    Copy comments from a gitlab to a github issue.

    :param gitlab_issue: the issue id on gitlab
    :param github_issue: the issue id on github
    """
    comments_map = {}
    for note in reversed(gitlab_issue.notes.list()):
        content = '**On {} {} ({}) wrote:**\n\n{}'.format(
                note.created_at.split('T')[0],
                note.author['name'],
                note.author['username'],
                sanitize_cross_links(note.body, gitlab_project, issues_map),
            )
        github_comment = github_issue.create_comment(content)
        if hasattr(github_comment, 'id'):
            comments_map[(gitlab_issue.id, note.id)] = (
                github_issue.id, github_comment.id) 
            _advise_manual_handling(github_comment, note)
        else:
            print('Error copying comment:\n{}'.format(github_comment))


def get_gitlab(gitlab_project):
    gitlab_api = gitlab.Gitlab(config.gitlab_url, private_token=config.gitlab_api_token)
    project = gitlab_api.projects.get(gitlab_project)
    return project


def get_github(github_repo):
    github_api = github.Github(config.github_api_token)
    project = github_api.get_repo(github_repo)
    return project


def get_from_gitlab_label(github_repo):
    name = "originally gitlab"
    try:
        from_gitlab_label = github_repo.get_label(name)
    except github.UnknownObjectException:
        descr = "For items that were originally created on gitlab and imported over"
        from_gitlab_label = github_repo.create_label(name, "ddd", descr)
    return from_gitlab_label


def make_issue_body(issue, gitlab_project, issues_map):
    linkback = "[gitlab issue {issue.iid}]({issue.web_url})"
    linkback = linkback.format(issue=issue)
    descr = sanitize_cross_links(issue.description, gitlab_project, issues_map)
    content = '**Imported from {}**\n\n{}'.format(linkback, descr)
    return content


def sanitize_cross_links(text, gitlab_repo, issue_map):
    def issue_replace(match):
        target_id = int(match.group(2))
        repl = "#%d" % issue_map[target_id].number
        return match.group(1) + repl + match.group(3)

    issue_re = re.compile(r"(\W|^)#(\d+)(\W|$)")
    tidied = issue_re.sub(issue_replace, text)

    def merge_request_replace(match):
        mr_id = int(match.group(2))
        mr = gitlab_repo.mergerequests.get(mr_id)
        return "%s[gitlab:!%d](%s)%s" % (match.group(1), mr_id, mr.web_url, match.group(3))

    merge_req_re = re.compile(r"(\W|^)!(\d+)(\W|$)")
    tidied = merge_req_re.sub(merge_request_replace, tidied)
    return tidied


def copy_labels(gitlab_project, github_repo):
    existing_labels = {l.name.lower(): l for l in github_repo.get_labels()}
    for label in gitlab_project.labels.list():
        print("Checking label:", label.name)
        clean_color = label.color
        clean_color = clean_color[1:] if clean_color.startswith("#") else clean_color
        new_label = existing_labels.get(label.name.lower(), None)
        if new_label:
            new_label.edit(label.name, clean_color)
            continue
        new_label = dict(name=label.name, color=clean_color)
        if label.description:
            new_label["description"] = label.description
        github_repo.create_label(**new_label)


def copy_issues(gitlab_issues, gitlab_project, github_repo, milestones_map):
    from_gitlab_label = get_from_gitlab_label(github_repo)
    usernames_map = config.usernames_map

    issues_map = {}
    for issue in gitlab_issues:
        print("Processing %d: %s" % (issue.iid,  issue.title))
        github_issue = dict(
            title=issue.title,
            body=make_issue_body(issue, gitlab_project, issues_map),
            labels=[from_gitlab_label] + issue.labels,
        )
        if issue.assignee:
            assignee = issue.assignee["username"]
            assignee = usernames_map.get(assignee, assignee)
            github_issue["assignee"] = assignee
        if issue.milestone:
            milestone = issue.milestone["id"]
            milestone = milestones_map.get(milestone, milestone)
            github_issue["milestone"] = milestone
        github_issue = github_repo.create_issue(**github_issue)
        if hasattr(github_issue, 'number'):
            issues_map[issue.iid] = github_issue
        else:
            print('Error copying issue:\n{}'.format(github_issue))
    return issues_map


def copy_issues_comments(gitlab_issues, gitlab_project, issues_map):
    for issue in gitlab_issues:
        print("Copying comments for %d: %s" % (issue.iid, issue.title))
        github_issue = issues_map[issue.iid]
        copy_issue_comments(issue, github_issue, gitlab_project, issues_map)
        if issue.state == 'closed':
            github_issue.edit(state="closed")


def gitlab2github(gitlab_project, github_repo, check_labels):
    """Copy issues from gitlab to github.

    :param gitlab_project: the project id on gitlab
    :type gitlab_project: int
    :param github_repo: the project name on github
    :type github_repo: str
    """
    gitlab_project = get_gitlab(gitlab_project)
    github_repo = get_github(github_repo)
    milestones_map = copy_milestones(gitlab_project, github_repo)
    gitlab_issues = gitlab_project.issues.list(sort="asc", all=True)

    if check_labels:
        copy_labels(gitlab_project, github_repo)

    issues_map = copy_issues(gitlab_issues, gitlab_project, github_repo, milestones_map)
    copy_issues_comments(gitlab_issues, gitlab_project, issues_map)
    return issues_map


def prepare_parser():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--gitlab-project", required=True, help="Source repo ID or name")
    parser.add_argument("--github-repo", required=True, help="Repo on github to push to")
    parser.add_argument("--no-check-labels", dest="check_labels", default=True,
                        action="store_false", help="Check labels first")
    return parser


if __name__ == '__main__':
    args = prepare_parser().parse_args()
    print(gitlab2github(**vars(args)))
