# AI agent skills

The `skills` directory contains skills for AI agents. Each skill is a self-contained folder with a `SKILL.md` and any supporting reference files that teach the agent how to work with a specific domain.

### Using all skills

To pull the entire `skills` folder into your own project using [git sparse-checkout](https://git-scm.com/docs/git-sparse-checkout):

```bash
# In your git project's root
git sparse-checkout init --cone
git remote add skills https://github.com/eamansour/skills.git
git fetch skills main
git sparse-checkout add skills
git checkout skills/main -- skills
```

### Using a single skill

To pull only one skill into your project's skills config directory:

```bash
# In your git project's root
git sparse-checkout init --cone
git remote add skills https://github.com/eamansour/skills.git
git fetch skills main
git checkout skills/main -- skills/dependency-update
```

Then move or copy the fetched folder into wherever your agent expects skills to live, for example `skills/dependency-update`.

> **Keeping skills up to date:** Re-run the `git checkout skills/main -- skills/<skill-name>` command to pull down the latest version of a skill at any time.
