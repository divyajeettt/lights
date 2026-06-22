## How to Work

1. Create a plan for the required task.
2. Wait for my manual review.
3. When starting the implementation:
  - Switch to main branch and pull in latest changes
  - Switch to a feature branch with an appropriate short name (do not start branch names with `codex/`)
  - Implement the changes on the feature branch
  - Wait for my manual review
4. Update the README.md file and tests according to the changes.
5. Run `isort --profile black` to sort the imports and `black` to format the python code.
6. To save the changes:
  - Delete PLAN.md, if created.
  - Commit all the touched files to git with an appropriate message.
  - Never commit files like PLAN.md, REVIEW.md, and CODEX.md to git.
  - Push the changes to origin.
  - Create a ready PR using gh with a helpful but concise description.
7. Post PR creation:
  - Spawn an independent sub-agent which reads the README.md file and reviews the PR.
  - Address the review comments which are necessary, update the README if needed, and commit and push.
  - Merge the PR.
  - Delete the feature branch from origin.
  - Switch back to main locally, pull in the latest changes, and delete the feature branch locally.

## Additional Instructions

- Do not touch the local .env file unless explicity asked to.
- Ignore the tests when creating the plan, and only update the tests once after the plan has been implemented.
