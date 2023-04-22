## Alice Skills Manager

Alice Skills Manager is a command line tool and a python module for interacting with the alce-skills repository. It allows querying the repository for information (skill listings, skill meta data, etc) and of course installing and removing skills from the system.

## Install

    pip install asm

## Usage

```python
from asm import AliceSkillsManager, SkillRepo, MultipleSkillMatches

asm = AliceSkillsManager(repo=SkillRepo(branch='master'))

# asm = AliceSkillsManager(platform='picroft', skills_dir='/some/path', repo=SkillRepo(branch='master', url='https://github.com/me/my-repo.git'))

print(asm.find_skill('bitcoin price'))
asm.install('bitcoin', 'dmp1ce')
print(asm.list())
print(asm.find_skill("https://github.com/JarbasAl/skill-stephen-hawking"))
asm.update()
asm.install_defaults()

try:
    asm.install('google')
except MultipleSkillMatches as e:
    e.skills[0].install()
```

```bash
asm -b master install bitcoin
asm -b master -p kde default
# ...
```

## TODO

- Parse readme.md from skills

## New Features

- Checks for skill_requirements.txt, will install skills listed there

## Credits

[JarbasAI/py_msm](https://github.com/JarbasAl/ZZZ-py_msm) and Mycroft AI
