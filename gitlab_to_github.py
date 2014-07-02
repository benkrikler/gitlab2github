#! /usr/bin/env python3

from collections import defaultdict
import gitlab_api
import github_api
import config
import re

def copy_milestones(gitlab_project, github_user, github_repo):
    """Copy milestones from gitlab to github.

    :param gitlab_project: the project id on gitlab
    :type gitlab_project: int
    :param github_user: the user to which the project is associated 
    :type github_user: str
    :param github_repo: the project name on github
    :type github_repo: str
    """
    milestones_map = {}
    gitlab_milestones = gitlab_api.request(
        '/projects/{}/milestones/'.format(gitlab_project))

    for milestone in gitlab_milestones:
        github_milestone = dict(
            title=milestone['title'], 
            description=milestone['description'], 
            state='open' if milestone['state'] == 'active' else 'closed', 
            due_on=milestone['due_date'],
        )
        github_milestone = github_api.request(
            '/repos/{}/{}/milestones'.format(github_user, github_repo),
            'POST',
            github_milestone
        )
        if 'number' in github_milestone:
            milestones_map[milestone['id']] = github_milestone['number']
        else:
            print('Error copying milestone:\n{}'.format(github_milestone))
    return milestones_map


def _advise_manual_handling(github_comment, gitlab_note, gitlab_issue, 
        github_issue, gitlab_project, github_user, github_repo):
    
    gitlab_url = gitlab_api.request(
            '/projects/{0}'.format(gitlab_project))['web_url']
    github_url = 'https://github.com/{}/{}/issues/{}#issuecomment-{}'.format(
            github_user, github_repo, github_issue,
            github_comment['id'],
        )
    if gitlab_note['attachment']:
        gitlab_url = '{}/issues/{}#note_{}'.format(
            gitlab_url, gitlab_issue, gitlab_note['id'])
        print(
            "You must copy the attachment {} from {} to {}".format(
                gitlab_note['attachment'], 
                gitlab_url,
                github_url,
            )
        )
    urls = re.findall('{}/.+'.format(config.gitlab_url), gitlab_note['body'])
    if urls:
        print(
            "The following urls on were internal to Gitlab, "
            "you may want to change them at {}: \n{}".format(
                github_url,    
                '\n'.join(urls)
            )
        )



def copy_issue_comments(gitlab_issue, github_issue, gitlab_project, 
        github_user, github_repo):
    """
    Copy comments from a gitlab to a github issue.

    :param gitlab_issue: the issue id on gitlab
    :type gitlab_issue: int
    :param github_issue: the issue id on github
    :type github_issue: int
    :param gitlab_project: the project id on gitlab
    :type gitlab_project: int
    :param github_user: the user to which the project is associated 
    :type github_user: str
    :param github_repo: the project name on github
    :type github_repo: str
    """
    comments_map = {}
    gitlab_notes = gitlab_api.request(
        '/projects/{}/issues/{}/notes'.format(gitlab_project, gitlab_issue)), 
    for note in reversed(gitlab_notes[0]):
        content = {
            'body': 'On {} {} ({}) wrote:\n{}'.format(
                note['author']['created_at'].split('T')[0],
                note['author']['username'],
                note['author']['email'],
                note['body'],
            )
        }
        github_comment = github_api.request(
            '/repos/{}/{}/issues/{}/comments'.format(
                github_user, github_repo, github_issue),
            'POST', 
            content,
        )
        if 'id' in github_comment:
            comments_map[(gitlab_issue, note['id'])] = (
                github_issue, github_comment['id']) 
            _advise_manual_handling(
                github_comment, note, 
                gitlab_issue, github_issue, 
                gitlab_project, github_user, github_repo,
            )
        else:
            print('Error copying comment:\n{}'.format(github_comment))



def copy_issues(gitlab_project, github_user, github_repo):
    """Copy issues from gitlab to github.

    :param gitlab_project: the project id on gitlab
    :type gitlab_project: int
    :param github_user: the user to which the project is associated 
    :type github_user: str
    :param github_repo: the project name on github
    :type github_repo: str
    """
    issues_map = {}
    milestones_map = copy_milestones(gitlab_project, github_user, github_repo)
    usernames_map = config.usernames_map
    gitlab_issues = gitlab_api.request(
        '/projects/{}/issues'.format(gitlab_project))

    for issue in gitlab_issues:
        assignee = issue['assignee']['username'] if issue['assignee'] else None
        milestone = issue['milestone']['id'] if issue['milestone'] else None
        github_issue = dict(
            title=issue['title'],
            body=issue['description'],
            labels=issue['labels'],
            assignee=usernames_map.get(assignee, None),
            milestone=milestones_map.get(milestone, milestone),
        )
        github_issue = github_api.request(
            '/repos/{}/{}/issues'.format(github_user, github_repo),
            'POST',
            github_issue,
        )
        if 'number' in github_issue:
            copy_issue_comments(issue['id'], github_issue['number'], 
                gitlab_project, github_user, github_repo)
            issues_map[issue['id']] = github_issue['number']
            if issue['state'] == 'closed':
                github_api.request(
                    '/repos/{}/{}/issues/{}'.format(
                        github_user, github_repo, github_issue['number']),
                    'PATCH',
                    {'state': 'closed'},
                )
        else:
            print('Error copying issue:\n{}'.format(github_issue))
    return issues_map


if __name__ == '__main__':
    #repo = 'rbsdev'
    #if 'url' in github_api.request( '/user/repos', 'POST', {'name': repo}):
    #    print('Created repo {}'.format(repo))
    print(copy_issues(2, 'rbsdev', 'sherlock'))
