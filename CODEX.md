# How to Work

1. Create a plan for the required task.
2. Wait for my manual review.
3. When starting the implementation:
  - Switch to main branch and pull in latest changes
  - Switch to a feature branch with an appropriate short name (do not start branch names with `codex/`)
  - Implement the changes on the feature branch
  - Wait for my manual review
4. Run `isort --profile black` to sort the imports and `black` to format the python code.
4. To save the changes:
  - Commit all the touched files to git with an appropriate message.
  - Never commit files like PLAN.md, REVIEW.md, and CODEX.md to git.
  - Push the changes to origin.
  - Create a PR with a helpful but concise description.
5. Post PR creation:
  - Spawn an independent sub-agent which reads the README.md file and reviews the PR.
  - Address the review comments which are necessary and commit and push.
  - Merge the PR.
  - Delete the feature branch from origin.
  - Switch back to main locally, pull in the latest changes, and delete the feature branch locally.