import logging
import sys
from logging import ERROR, INFO

from asm.exceptions import AsmException
from asm.alice_skills_manager import AliceSkillsManager
from asm.skill_repo import SkillRepo

LOG = logging.getLogger(__name__)


def get_error_code(error_cls):
    return 1 + (sum(map(ord, error_cls.__name__)) % 255)


def skill_info(skill):
    print('\n'.join([
        'Name: ' + skill.name,
        'Author: ' + str(skill.author),
        'Url: ' + str(skill.url),
        'Path: ' + (str(skill.path) if skill.is_local else 'Not installed')
    ]))


def main(args=None, printer=print):
    logging.basicConfig(level=INFO, format='%(levelname)s - %(message)s')

    import argparse
    platforms = list(AliceSkillsManager.SKILL_GROUPS)
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--platform', choices=platforms,
                        default='default')
    parser.add_argument('-u', '--repo-url')
    parser.add_argument('-b', '--repo-branch')
    parser.add_argument('-d', '--skills-dir')
    parser.add_argument('-l', '--latest', action='store_false',
                        dest='versioned', help="Disable skill versioning")
    parser.add_argument('-r', '--raw', action='store_true')
    parser.set_defaults(raw=False, versioned=True)
    subparsers = parser.add_subparsers(dest='action')
    subparsers.required = True

    def add_constraint_args(subparser):
        subparser.add_argument('--constraints',
                               help='limit the installed requirements using '
                                    'a pip constraint.txt file.')

    def add_search_args(subparser, skill_is_optional=False):
        if skill_is_optional:
            subparser.add_argument('skill', nargs='?')
        else:
            subparser.add_argument('skill')
        subparser.add_argument('author', nargs='?')

    install_parser = subparsers.add_parser('install')
    add_search_args(install_parser)
    add_constraint_args(install_parser)
    add_search_args(subparsers.add_parser('remove'))
    add_search_args(subparsers.add_parser('search'))
    add_search_args(subparsers.add_parser('info'))
    subparsers.add_parser('list').add_argument('-i', '--installed',
                                               action='store_true')
    add_search_args(subparsers.add_parser('update'), skill_is_optional=True)
    subparsers.add_parser('default')
    args = parser.parse_args(args or sys.argv[1:])

    if args.raw:
        LOG.level = ERROR

    repo = SkillRepo(
        url=args.repo_url, branch=args.repo_branch
    )
    asm = AliceSkillsManager(
        platform=args.platform, repo=repo, skills_dir=args.skills_dir, versioned=args.versioned
    )
    main_functions = {
        'install': lambda: asm.install(args.skill, args.author,
                                       args.constraints, 'cli'),
        'remove': lambda: asm.remove(args.skill, args.author),
        'list': lambda: '\n'.join(
            skill.name + (
                '\t[installed]' if skill.is_local and not args.raw else ''
            )
            for skill in asm.list()
            if not args.installed or skill.is_local
        ),
        'update': lambda: asm.update(args.skill, args.author),
        'default': asm.install_defaults,
        'search': lambda: '\n'.join(
            skill.name
            for skill in asm.list()
            if skill.match(args.skill, args.author) >= 0.3
        ),
        'info': lambda: skill_info(asm.find_skill(args.skill, args.author))
    }
    with asm.lock:
        try:
            result = main_functions[args.action]()
            if result is False:
                return 1
            if isinstance(result, str):
                printer(result)
            return 0
        except AsmException as e:
            exc_type = e.__class__.__name__
            printer('{}: {}'.format(exc_type, str(e)))
            return get_error_code(e.__class__)


if __name__ == "__main__":
    main()
