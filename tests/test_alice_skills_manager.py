import json
import os
from os.path import dirname, join
import tempfile
from pathlib import Path
from shutil import copyfile, rmtree
from unittest import TestCase

from unittest.mock import call, Mock, patch

from alice_skills_manager import AliceSkillsManager, AlreadyInstalled, AlreadyRemoved
from alice_skills_manager.exceptions import AsmException
from alice_skills_manager.skill_state import device_skill_state_hash


class TestAliceSkillsManager(TestCase):
    def setUp(self):
        temp_dir = tempfile.mkdtemp()
        self.temp_dir = Path(temp_dir)
        self.skills_json_path = self.temp_dir.joinpath('skills.json')
        self.skills_dir = self.temp_dir.joinpath('skills')
        self._build_fake_skills()
        self._mock_skills_json_path()
        self._mock_skill_entry()
        self._mock_skill_repo()
        copyfile(join(dirname(__file__), 'skills_test.json'),
                 str(self.skills_json_path))
        self.asm = AliceSkillsManager(
            platform='default',
            skills_dir=str(self.temp_dir.joinpath('skills')),
            repo=self.skill_repo_mock,
            versioned=True
        )

    def _build_fake_skills(self):
        foo_skill_dir = self.skills_dir.joinpath('skill-foo')
        foo_skill_dir.mkdir(parents=True)
        foo_skill_dir.joinpath('__init__.py').touch()
        bar_skill_dir = self.skills_dir.joinpath('skill-bar')
        bar_skill_dir.mkdir(parents=True)
        bar_skill_dir.joinpath('__init__.py').touch()

    def _mock_log(self):
        log_patch = patch('asm.alice_skills_manager.LOG')
        self.addCleanup(log_patch.stop)
        self.log_mock = log_patch.start()

    def _mock_skills_json_path(self):
        savedatapath_patch = patch('asm.skill_state.get_state_path')
        self.skills_json_path_mock = savedatapath_patch.start()
        self.skills_json_path_mock.return_value = str(
            self.temp_dir.joinpath('skills.json')
        )

        self.addCleanup(savedatapath_patch.stop)

    def _mock_skill_entry(self):
        skill_entry_patch = patch(
            'asm.alice_skills_manager.SkillEntry.install',
            spec=True
        )
        self.addCleanup(skill_entry_patch.stop)
        self.skill_entry_mock = skill_entry_patch.start()

    def _mock_skill_repo(self):
        skill_repo_patch = patch(
            'asm.alice_skills_manager.SkillRepo',
            spec=True

        )
        self.addCleanup(skill_repo_patch.stop)
        self.skill_repo_mock = skill_repo_patch.start()
        self.skill_repo_mock.skills_meta_info = {
            'https://skill_foo_url': None
        }

    def teardown(self):
        rmtree(str(self.temp_dir))

    def test_device_skill_state(self):
        """Contents of skills.json are loaded into memory"""
        state = self.asm.device_skill_state
        initial_state = [
            dict(
                name='skill-foo',
                origin='default',
                beta=False,
                status='active',
                installed=12345,
                updated=0,
                installation='installed',
                skill_gid='@|skill-foo'
            ),
            dict(
                name='skill-bar',
                origin='default',
                beta=False,
                status='active',
                installed=23456,
                updated=0,
                installation='installed',
                skill_gid='@|skill-bar'
            )
        ]

        self.assertListEqual(initial_state, state['skills'])
        self.assertListEqual([], state['blacklist'])
        self.assertEqual(2, state['version'])

        new_hash = device_skill_state_hash(self.asm.device_skill_state)
        self.assertEqual(new_hash, self.asm.device_skill_state_hash)

    def test_build_device_skill_state(self):
        """No skill.json file so build one."""
        os.remove(str(self.skills_json_path))
        self.asm._device_skill_state = None
        self.asm._init_skills_data()
        state = self.asm.device_skill_state

        initial_state = [
            dict(
                name='skill-bar',
                origin='non-asm',
                beta=False,
                status='active',
                installed=0,
                updated=0,
                installation='installed',
                skill_gid='@|skill-bar'
            ),
            dict(
                name='skill-foo',
                origin='non-asm',
                beta=False,
                status='active',
                installed=0,
                updated=0,
                installation='installed',
                skill_gid='@|skill-foo'
            )
        ]

        self.assertTrue(self.skills_json_path.exists())
        with open(str(self.skills_json_path)) as skills_json:
            device_skill_state = json.load(skills_json)
        self.assertListEqual(sorted(initial_state, key=lambda x: x['name']),
                             sorted(device_skill_state['skills'], key=lambda x: x['name']))
        self.assertListEqual(sorted(initial_state, key=lambda x: x['name']),
                             sorted(device_skill_state['skills'], key=lambda x: x['name']))
        self.assertListEqual([], state['blacklist'])
        self.assertListEqual([], device_skill_state['blacklist'])
        self.assertEqual(2, state['version'])
        self.assertEqual(2, device_skill_state['version'])
        new_hash = device_skill_state_hash(self.asm.device_skill_state)
        self.assertEqual(new_hash, self.asm.device_skill_state_hash)

    def test_remove_from_device_skill_state(self):
        """Remove a file no longer installed from the device's skill state.

        Delete skill-bar from the local skills.  This should trigger it being
        removed from the device skill state.
        """

        del(self.asm.local_skills['skill-bar'])
        self.asm._device_skill_state = None
        state = self.asm.device_skill_state

        initial_state = [
            dict(
                name='skill-foo',
                origin='default',
                beta=False,
                status='active',
                installed=12345,
                updated=0,
                installation='installed',
                skill_gid='@|skill-foo'
            )
        ]

        self.assertListEqual(initial_state, state['skills'])
        self.assertListEqual([], state['blacklist'])
        self.assertEqual(2, state['version'])

    def test_skill_list(self):
        """The skill.list() method is called."""
        all_skills = self.asm.list()

        skill_names = [skill.name for skill in all_skills]
        self.assertIn('skill-foo', skill_names)
        self.assertIn('skill-bar', skill_names)
        self.assertEqual(2, len(all_skills))
        self.assertIsNone(self.asm._local_skills)
        self.assertIsNone(self.asm._default_skills)
        self.assertEqual(all_skills, self.asm._all_skills)

    def test_install(self):
        """Install a skill

        Test that the install method was called on the skill being installed
        and that the new skill was added to the device's skill state.
        """
        skill_to_install = self.skill_entry_mock()
        skill_to_install.name = 'skill-test'
        skill_to_install.skill_gid = 'test-skill|99.99'
        skill_to_install.is_beta = False
        with patch('asm.alice_skills_manager.isinstance') as isinstance_mock:
            isinstance_mock.return_value = True
            with patch('asm.alice_skills_manager.time') as time_mock:
                time_mock.time.return_value = 100
                self.asm.install(skill_to_install, origin='voice')

        with open(str(self.skills_json_path)) as skills_json:
            device_skill_state = json.load(skills_json)

        skill_test_state = dict(
            name='skill-test',
            origin='voice',
            beta=False,
            status='active',
            installed=100,
            updated=0,
            installation='installed',
            skill_gid='test-skill|99.99'
        )
        self.assertIn(skill_test_state, device_skill_state['skills'])
        self.assertListEqual(
            [call.install(None)],
            skill_to_install.method_calls
        )

    def test_already_installed(self):
        """Attempt install of skill already on the device.

        When this happens, an AlreadyInstalled exception is raised and the
        device skill state is not modified.
        """
        skill_to_install = self.skill_entry_mock()
        skill_to_install.name = 'skill-foo'
        skill_to_install.skill_gid = 'skill-foo|99.99'
        skill_to_install.is_beta = False
        skill_to_install.install = Mock(side_effect=AlreadyInstalled())
        pre_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        with patch('asm.alice_skills_manager.isinstance') as isinstance_mock:
            isinstance_mock.return_value = True
            with self.assertRaises(AlreadyInstalled):
                self.asm.install(skill_to_install)

        self.assertIsNotNone(self.asm._local_skills)
        self.assertIn('all_skills', self.asm._cache)
        post_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        self.assertEqual(pre_install_hash, post_install_hash)

    def test_install_failure(self):
        """Install attempt fails for whatever reason

        When an install fails, the installation will raise a AsmException.  The
        skill install will be saved to the device skill state as failed and
        the error that caused the exception will be included in the state.
        """
        skill_to_install = self.skill_entry_mock()
        skill_to_install.name = 'skill-test'
        skill_to_install.skill_gid = 'skill-test|99.99'
        skill_to_install.is_beta = False
        skill_to_install.install = Mock(side_effect=AsmException('RED ALERT!'))
        with patch('asm.alice_skills_manager.isinstance') as isinstance_mock:
            with self.assertRaises(AsmException):
                isinstance_mock.return_value = True
                self.asm.install(skill_to_install, origin='cli')

        with open(str(self.skills_json_path)) as skills_json:
            device_skill_state = json.load(skills_json)

        skill_test_state = dict(
            name='skill-test',
            origin='cli',
            beta=False,
            status='error',
            installed=0,
            updated=0,
            installation='failed',
            skill_gid='skill-test|99.99',
            failure_message='RED ALERT!'
        )
        self.assertIn(skill_test_state, self.asm.device_skill_state['skills'])
        self.assertIn(skill_test_state, device_skill_state['skills'])
        self.assertListEqual(
            [call.install(None)],
            skill_to_install.method_calls
        )

    def test_remove(self):
        """Remove a skill

        Test that the remove method was called on the skill being installed
        and that the new skill was removed from the device's skill state.
        """
        skill_to_remove = self.skill_entry_mock()
        skill_to_remove.name = 'skill-foo'
        pre_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        with patch('asm.alice_skills_manager.isinstance') as isinstance_mock:
            isinstance_mock.return_value = True
            self.asm.remove(skill_to_remove)

        with open(str(self.skills_json_path)) as skills_json:
            device_skill_state = json.load(skills_json)

        skill_names = [skill['name'] for skill in device_skill_state['skills']]
        self.assertNotIn('skill_foo', skill_names)
        skill_names = [
            skill['name'] for skill in self.asm.device_skill_state['skills']
        ]
        self.assertNotIn('skill_foo', skill_names)
        self.assertListEqual([call.remove()], skill_to_remove.method_calls)
        self.assertNotIn('all_skills', self.asm._cache)
        self.assertIsNone(self.asm._local_skills)
        post_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        self.assertNotEqual(pre_install_hash, post_install_hash)

    def test_already_removed(self):
        """Attempt removal of skill already removed from the device.

        When this happens, an AlreadyRemoved exception is raised and the
        device skill state is not modified.
        """
        skill_to_remove = self.skill_entry_mock()
        skill_to_remove.name = 'skill-foo'
        skill_to_remove.remove = Mock(side_effect=AlreadyRemoved())
        pre_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        with patch('asm.alice_skills_manager.isinstance') as isinstance_mock:
            isinstance_mock.return_value = True
            with self.assertRaises(AlreadyRemoved):
                self.asm.remove(skill_to_remove)

        self.assertListEqual([call.remove()], skill_to_remove.method_calls)
        self.assertIsNotNone(self.asm._local_skills)
        self.assertIn('all_skills', self.asm._cache)
        post_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        self.assertEqual(pre_install_hash, post_install_hash)

    def test_remove_failure(self):
        """Skill removal attempt fails for whatever reason

        When n removal fails, a AsmException is raised.  The removal will not
        be saved to the device skill state.
        """
        skill_to_remove = self.skill_entry_mock()
        skill_to_remove.name = 'skill-test'
        skill_to_remove.remove = Mock(side_effect=AsmException('RED ALERT!'))
        pre_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        with patch('asm.alice_skills_manager.isinstance') as isinstance_mock:
            isinstance_mock.return_value = True
            with self.assertRaises(AsmException):
                self.asm.remove(skill_to_remove)

        self.assertListEqual(
            [call.remove()],
            skill_to_remove.method_calls
        )
        self.assertIsNotNone(self.asm._local_skills)
        self.assertIn('all_skills', self.asm._cache)
        post_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        self.assertEqual(pre_install_hash, post_install_hash)

    def test_update(self):
        """Remove a skill

        Test that the remove method was called on the skill being installed
        and that the new skill was removed from the device's skill state.
        """
        skill_to_update = self.skill_entry_mock()
        skill_to_update.name = 'skill-foo'
        skill_to_update.is_beta = False
        pre_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        with patch('asm.alice_skills_manager.time') as time_mock:
            time_mock.time.return_value = 100
            self.asm.update(skill_to_update)

        with open(str(self.skills_json_path)) as skills_json:
            device_skill_state = json.load(skills_json)

        skill_names = [skill['name'] for skill in device_skill_state['skills']]
        self.assertIn('skill-foo', skill_names)

        for skill in self.asm.device_skill_state['skills']:
            if skill['name'] == 'skill-foo':
                self.assertEqual(100, skill['updated'])
        self.assertListEqual([call.update()], skill_to_update.method_calls)
        self.assertNotIn('all_skills', self.asm._cache)
        self.assertIsNone(self.asm._local_skills)
        post_install_hash = device_skill_state_hash(
            self.asm.device_skill_state
        )
        self.assertNotEqual(pre_install_hash, post_install_hash)
