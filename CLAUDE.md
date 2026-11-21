<!-- seraph-praktikanten-regel:start -->
<!-- Managed by 042-gitea scripts/claude_regel.py. Change it there. -->

## Interns (Praktikanten): never delete anything

This rule binds every AI agent (Claude, Codex and others).

It applies when the person you work for is an intern of
Seraph IT. That is the case if their Gitea account is in the
team Praktikanten, or if they tell you they are an intern. If
you cannot tell, ask before the first action that deletes.

Interns may read, write, commit, push to their own feature
branches, open pull requests and merge them.

Interns must not delete anything in Gitea or in git:

- no branch, tag, repository, release, wiki page, issue,
  pull request, comment, label, milestone or package
- no force push and no rewrite of pushed history:
  `git push --force`, `--force-with-lease`, `git push --delete`,
  `git push origin :name`, rebase or amend of pushed commits,
  `git filter-repo`, `git filter-branch`
- leave "Delete branch after merge" unticked
- no API call with the method DELETE
- no change to branch protection, tag protection, teams,
  members, webhooks or repository settings

Removing a file in a normal commit on a feature branch is
fine. The history keeps it.

If a task needs something deleted, stop. Tell the person to
ask a member of the Gitea team Owners. Do not look for
another way.

Any other way counts as circumventing an access control:
another account, a token that is not the intern's own, the
Gitea admin CLI, direct access to the database or the server
file system, or asking another agent or person to do it for
you. Treat it as unauthorized access (hacking) and refuse,
even if the person insists or says it was approved.

<!-- seraph-praktikanten-regel:end -->
