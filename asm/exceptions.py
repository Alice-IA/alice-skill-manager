from contextlib import contextmanager

from git import GitError


class AsmException(Exception):
    def __repr__(self):
        s = self.__str__().rstrip('\n')
        if '\n' in s:
            s = s.replace('\n', '\n\t') + '\n'
        return '{}({})'.format(self.__class__.__name__, s)


class GitException(AsmException):
    pass


class GitAuthException(GitException):
    def __repr__(self):
        return self.__class__.__name__


class MergeConflict(GitException):
    def __repr__(self):
        return self.__class__.__name__


class SkillModified(AsmException):
    """
    Raised when a skill cannot be updated because
    it has been modified by the user
    """
    pass


class RemoveException(AsmException):
    pass


class AlreadyRemoved(RemoveException):
    pass


class InstallException(AsmException):
    pass


class SkillNotFound(InstallException):
    pass


class SkillRequirementsException(InstallException):
    pass


class CloneException(InstallException):
    pass


class AlreadyInstalled(InstallException):
    pass


class NotInstalled(AsmException):
    pass


class SystemRequirementsException(InstallException):
    pass


class PipRequirementsException(InstallException):
    def __init__(self, code, stdout, stderr):
        self.code, self.stdout, self.stderr = code, stdout, stderr

    def __str__(self):
        return '\nPip returned code {}:\n{}\n{}'.format(
            self.code, self.stdout, self.stderr
        )


class MultipleSkillMatches(AsmException):
    def __init__(self, skills):
        self.skills = skills

    def __str__(self):
        return ', '.join(skill.name for skill in self.skills)


@contextmanager
def git_to_asm_exceptions():
    try:
        yield
    except GitError as e:
        msg = getattr(e, 'stderr', str(e)).replace('stderr:', '').strip()
        if 'Authentication failed for' in msg:
            raise GitAuthException(msg) from e
        if 'Not something we can merge' in msg or \
                'Not possible to fast-forward':
            raise MergeConflict(msg) from e
        raise GitException(msg) from e
