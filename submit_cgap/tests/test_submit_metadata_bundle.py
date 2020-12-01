import pytest

from dcicutils.misc_utils import ignored
from dcicutils.qa_utils import override_environ
from unittest import mock
from ..base import KeyManager
from ..scripts.submit_metadata_bundle import main as submit_metadata_bundle_main
from ..scripts import submit_metadata_bundle as submit_metadata_bundle_module


@pytest.mark.parametrize("keyfile", [None, "foo.bar"])
def test_submit_metadata_bundle_script(keyfile):

    def test_it(args_in, expect_exit_code, expect_called, expect_call_args=None):

        with override_environ(CGAP_KEYS_FILE=keyfile):
            with mock.patch.object(submit_metadata_bundle_module,
                                   "submit_metadata_bundle") as mock_submit_metadata_bundle:
                try:
                    # Outside of the call, we will always see the default filename for cgap keys
                    # but inside the call, because of a decorator, the default might be different.
                    # See additional test below.
                    assert KeyManager.keydicts_filename() == KeyManager.DEFAULT_KEYDICTS_FILENAME

                    def mocked_submit_metadata_bundle(*args, **kwargs):
                        ignored(args, kwargs)
                        # We don't need to test this function's actionsusin because we test its call args below.
                        # However, we do need to run this one test from the same dynamic context,
                        # so this is close enough.
                        assert KeyManager.keydicts_filename() == (keyfile or KeyManager.DEFAULT_KEYDICTS_FILENAME)

                    mock_submit_metadata_bundle.side_effect = mocked_submit_metadata_bundle
                    submit_metadata_bundle_main(args_in)
                    mock_submit_metadata_bundle.assert_called_with(**expect_call_args)
                except SystemExit as e:
                    assert e.code == expect_exit_code
                assert mock_submit_metadata_bundle.call_count == (1 if expect_called else 0)

    test_it(args_in=[], expect_exit_code=2, expect_called=False)  # Missing args
    test_it(args_in=['some-file'], expect_exit_code=0, expect_called=True, expect_call_args={
        'bundle_filename': 'some-file',
        'env': None,
        'server': None,
        'institution': None,
        'project': None,
        'validate_only': False,
    })
    expect_call_args = {
        'bundle_filename': 'some-file',
        'env': "some-env",
        'server': "some-server",
        'institution': "some-institution",
        'project': "some-project",
        'validate_only': True,
    }
    test_it(args_in=["--env", "some-env", "--institution", "some-institution",
                     "-s", "some-server", "-v", "-p", "some-project",
                     'some-file'],
            expect_exit_code=0,
            expect_called=True,
            expect_call_args=expect_call_args)
    test_it(args_in=["some-file", "--env", "some-env", "--institution", "some-institution",
                     "-s", "some-server", "--validate-only", "--project", "some-project"],
            expect_exit_code=0,
            expect_called=True,
            expect_call_args=expect_call_args)
