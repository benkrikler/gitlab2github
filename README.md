gitlab2github
=============

Copies issues from Gitlab to Github. It is useful when you are migrating a Gitlab project to Github.
Although source code and wiki can be easily migrated using git, the issues and their revealing story would be left behind.


## Installing dependencies

Having Python and pip installed, you can install the project's dependencies issuing the following command:

```bash
pip install -r requirements.txt
```

## Usage

First, enter your api keys on the config.py file.

Gitlab token: http://git.strikingcode.com/profile/account

Github token: https://github.com/settings/applications

You can then import the copy_issues method from the gitlab_to_github module:

```python
copy_issues(gitlab_repo=2, github_user='rbsdev', github_repo='test')
```

Since [Github's comment API](https://developer.github.com/v3/issues/comments/) doesn't provide a way to add attachments, the attachments on the Gitlab issues are printed to the output, so that you can manually copy them if needed.



