# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Unit test suite for ``aws_encryption_sdk_cli``."""
import os

import aws_encryption_sdk
from mock import ANY, call, MagicMock, sentinel
import pytest

import aws_encryption_sdk_cli
from aws_encryption_sdk_cli.exceptions import AWSEncryptionSDKCLIError, BadUserArgumentError


def patch_reactive_side_effect(kwargs):
    def _check(path):
        return kwargs[path]
    return _check


@pytest.yield_fixture
def patch_process_dir(mocker):
    mocker.patch.object(aws_encryption_sdk_cli, 'process_dir')
    yield aws_encryption_sdk_cli.process_dir


@pytest.yield_fixture
def patch_process_single_file(mocker):
    mocker.patch.object(aws_encryption_sdk_cli, 'process_single_file')
    yield aws_encryption_sdk_cli.process_single_file


@pytest.yield_fixture
def patch_output_filename(mocker):
    mocker.patch.object(aws_encryption_sdk_cli, 'output_filename')
    aws_encryption_sdk_cli.output_filename.return_value = sentinel.destination_filename


@pytest.fixture
def patch_for_process_cli_request(mocker, patch_process_dir, patch_process_single_file):
    mocker.patch.object(aws_encryption_sdk_cli, 'process_single_operation')


def test_process_cli_request_source_is_destination_dir_to_dir(tmpdir):
    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli.process_cli_request(
            stream_args={'mode': 'encrypt'},
            source=str(tmpdir),
            destination=str(tmpdir),
            recursive=True,
            interactive=False,
            no_overwrite=False
        )
    excinfo.match(r'Destination and source cannot be the same')


def test_catch_bad_destination_requests_stdout():
    aws_encryption_sdk_cli._catch_bad_destination_requests('-')


def test_catch_bad_destination_requests_dir(tmpdir):
    aws_encryption_sdk_cli._catch_bad_destination_requests(str(tmpdir))


def test_catch_bad_destination_requests_file(tmpdir):
    destination = tmpdir.join('dir1', 'dir2', 'file')
    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli._catch_bad_destination_requests(str(destination))

    assert excinfo.match(r'If destination is a file, the immediate parent directory must already exist.')


def test_catch_bad_stdin_stdout_requests_same_pipe():
    aws_encryption_sdk_cli._catch_bad_stdin_stdout_requests('-', '-')


def test_catch_bad_stdin_stdout_requests_same_file(tmpdir):
    source = tmpdir.join('test_file')
    source.write('some_data')

    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli._catch_bad_stdin_stdout_requests(str(source), str(source))

    excinfo.match(r'Destination and source cannot be the same')


def test_catch_bad_stdin_stdout_requests_same_file_symlink(tmpdir):
    source = tmpdir.join('test_file')
    source.write('some_data')
    link_dest = str(tmpdir.join('destination'))
    os.symlink(str(source), link_dest)

    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli._catch_bad_stdin_stdout_requests(str(source), link_dest)

    excinfo.match(r'Destination and source cannot be the same')


def test_catch_bad_stdin_stdout_requests_same_dir(tmpdir):
    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli._catch_bad_stdin_stdout_requests(str(tmpdir), str(tmpdir))

    excinfo.match(r'Destination and source cannot be the same')


def test_catch_bad_stdin_stdout_requests_same_dir_symlink(tmpdir):
    link_dest = str(tmpdir.join('destination'))
    os.symlink(str(tmpdir), link_dest)

    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli._catch_bad_stdin_stdout_requests(str(tmpdir), link_dest)

    excinfo.match(r'Destination and source cannot be the same')


def test_catch_bad_stdin_stdout_requests_dest_links_source(tmpdir):
    source = tmpdir.join('source')
    source.write('some data')
    linked_source = str(tmpdir.join('link_to_source'))
    os.symlink(str(source), linked_source)

    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli._catch_bad_stdin_stdout_requests(str(source), linked_source)

    excinfo.match(r'Destination and source cannot be the same')


def test_catch_bad_stdin_stdout_requests_stdin_dir(tmpdir):
    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli._catch_bad_stdin_stdout_requests('-', str(tmpdir))

    excinfo.match(r'Destination may not be a directory when source is stdin')


def test_catch_bad_file_and_directory_requests_multiple_source_nondir_destination(tmpdir):
    a = tmpdir.join('a')
    a.write('asdf')
    b = tmpdir.join('b')
    b.write('asdf')

    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli._catch_bad_file_and_directory_requests((str(a), str(b)), str(tmpdir.join('c')))

    excinfo.match(r'If operating on multiple sources, destination must be an existing directory')


def test_catch_bad_file_and_directory_requests_contains_dir(tmpdir):
    b = tmpdir.mkdir('b')

    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli._catch_bad_file_and_directory_requests((str(b),), str(tmpdir.join('c')))

    excinfo.match(r'If operating on a source directory, destination must be an existing directory')


def test_process_cli_request_source_is_destination_file_to_file(tmpdir):
    single_file = tmpdir.join('a_file')
    single_file.write('some data')

    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli.process_cli_request(
            stream_args={'mode': 'encrypt'},
            source=str(single_file),
            destination=str(single_file),
            recursive=True,
            interactive=False,
            no_overwrite=False
        )
    excinfo.match(r'Destination and source cannot be the same')


def test_process_cli_request_source_dir_nonrecursive(tmpdir, patch_for_process_cli_request):
    source = tmpdir.mkdir('source')
    destination = tmpdir.mkdir('destination')
    aws_encryption_sdk_cli.process_cli_request(
        stream_args=sentinel.stream_args,
        source=str(source),
        destination=str(destination),
        recursive=False,
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite
    )

    assert not aws_encryption_sdk_cli.process_single_operation.called
    assert not aws_encryption_sdk_cli.process_dir.called
    assert not aws_encryption_sdk_cli.process_single_file.called


def test_process_cli_request_source_dir_destination_nondir(tmpdir):
    source = tmpdir.mkdir('source')
    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli.process_cli_request(
            stream_args={'mode': 'encrypt'},
            source=str(source),
            destination=str(tmpdir.join('destination')),
            recursive=True,
            interactive=False,
            no_overwrite=False
        )
    excinfo.match(r'If operating on a source directory, destination must be an existing directory')


def test_process_cli_request_source_dir_destination_dir(tmpdir, patch_for_process_cli_request):
    source = tmpdir.mkdir('source_dir')
    destination = tmpdir.mkdir('destination_dir')
    aws_encryption_sdk_cli.process_cli_request(
        stream_args=sentinel.stream_args,
        source=str(source),
        destination=str(destination),
        recursive=True,
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite,
        suffix=sentinel.suffix
    )

    aws_encryption_sdk_cli.process_dir.assert_called_once_with(
        stream_args=sentinel.stream_args,
        source=str(source),
        destination=str(destination),
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite,
        suffix=sentinel.suffix
    )
    assert not aws_encryption_sdk_cli.process_single_file.called
    assert not aws_encryption_sdk_cli.process_single_operation.called


def test_process_cli_request_source_stdin_destination_dir(tmpdir):
    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli.process_cli_request(
            stream_args={'mode': 'encrypt'},
            source='-',
            destination=str(tmpdir),
            recursive=False,
            interactive=False,
            no_overwrite=False
        )
    excinfo.match(r'Destination may not be a directory when source is stdin')


def test_process_cli_request_source_stdin(tmpdir, patch_for_process_cli_request):
    destination = tmpdir.join('destination')
    aws_encryption_sdk_cli.process_cli_request(
        stream_args=sentinel.stream_args,
        source='-',
        destination=str(destination),
        recursive=False,
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite
    )
    assert not aws_encryption_sdk_cli.process_dir.called
    assert not aws_encryption_sdk_cli.process_single_file.called
    aws_encryption_sdk_cli.process_single_operation.assert_called_once_with(
        stream_args=sentinel.stream_args,
        source='-',
        destination=str(destination),
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite
    )


def test_process_cli_request_source_file_destination_dir(tmpdir, patch_for_process_cli_request):
    source = tmpdir.join('source')
    source.write('some data')
    destination = tmpdir.mkdir('destination')
    aws_encryption_sdk_cli.process_cli_request(
        stream_args={'mode': sentinel.mode},
        source=str(source),
        destination=str(destination),
        recursive=False,
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite,
        suffix='CUSTOM_SUFFIX'
    )
    assert not aws_encryption_sdk_cli.process_dir.called
    assert not aws_encryption_sdk_cli.process_single_operation.called
    aws_encryption_sdk_cli.process_single_file.assert_called_once_with(
        stream_args={'mode': sentinel.mode},
        source=str(source),
        destination=str(destination.join('sourceCUSTOM_SUFFIX')),
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite
    )


def test_process_cli_request_source_file_destination_file(tmpdir, patch_for_process_cli_request):
    source = tmpdir.join('source')
    source.write('some data')
    destination = tmpdir.join('destination')

    aws_encryption_sdk_cli.process_cli_request(
        stream_args={'mode': sentinel.mode},
        source=str(source),
        destination=str(destination),
        recursive=False,
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite
    )
    assert not aws_encryption_sdk_cli.process_dir.called
    assert not aws_encryption_sdk_cli.process_single_operation.called
    aws_encryption_sdk_cli.process_single_file.assert_called_once_with(
        stream_args={'mode': sentinel.mode},
        source=str(source),
        destination=str(destination),
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite
    )


def test_process_cli_request_invalid_source(tmpdir):
    target = os.path.join(str(tmpdir), 'test_targets.*')
    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli.process_cli_request(
            stream_args={},
            source=target,
            destination='a specific destination',
            recursive=False,
            interactive=False,
            no_overwrite=False
        )
    excinfo.match(r'Invalid source.  Must be a valid pathname pattern or stdin \(-\)')


def test_process_cli_request_globbed_source_non_directory_target(tmpdir, patch_process_dir, patch_process_single_file):
    plaintext_dir = tmpdir.mkdir('plaintext')
    test_file = plaintext_dir.join('testing.aa')
    test_file.write(b'some data here!')
    test_file = plaintext_dir.join('testing.bb')
    test_file.write(b'some data here!')
    ciphertext_dir = tmpdir.mkdir('ciphertext')
    target_file = ciphertext_dir.join('target_file')
    source = os.path.join(str(plaintext_dir), 'testing.*')

    with pytest.raises(BadUserArgumentError) as excinfo:
        aws_encryption_sdk_cli.process_cli_request(
            stream_args={'mode': 'encrypt'},
            source=source,
            destination=str(target_file),
            recursive=False,
            interactive=False,
            no_overwrite=False
        )

    excinfo.match('If operating on multiple sources, destination must be an existing directory')
    assert not patch_process_dir.called
    assert not patch_process_single_file.called


def test_process_cli_request_source_contains_directory_nonrecursive(
        tmpdir,
        patch_process_dir,
        patch_process_single_file
):
    plaintext_dir = tmpdir.mkdir('plaintext')
    test_file_a = plaintext_dir.join('testing.aa')
    test_file_a.write(b'some data here!')
    test_file_c = plaintext_dir.join('testing.cc')
    test_file_c.write(b'some data here!')
    plaintext_dir.mkdir('testing.bb')
    ciphertext_dir = tmpdir.mkdir('ciphertext')
    source = os.path.join(str(plaintext_dir), 'testing.*')

    aws_encryption_sdk_cli.process_cli_request(
        stream_args={'mode': 'encrypt'},
        source=source,
        destination=str(ciphertext_dir),
        recursive=False,
        interactive=False,
        no_overwrite=False
    )

    assert not patch_process_dir.called
    patch_process_single_file.assert_has_calls(
        calls=[
            call(
                stream_args={'mode': 'encrypt'},
                source=str(source_file),
                destination=ANY,
                interactive=False,
                no_overwrite=False
            )
            for source_file in (test_file_a, test_file_c)
        ],
        any_order=True
    )


@pytest.mark.parametrize('args, stream_args', (
    (
        MagicMock(
            action=sentinel.mode,
            encryption_context=None,
            algorithm=None,
            frame_length=None,
            max_length=None
        ),
        {
            'materials_manager': sentinel.materials_manager,
            'mode': sentinel.mode
        }
    ),
    (
        MagicMock(
            action=sentinel.mode,
            encryption_context=None,
            algorithm=None,
            frame_length=None,
            max_length=sentinel.max_length
        ),
        {
            'materials_manager': sentinel.materials_manager,
            'mode': sentinel.mode,
            'max_body_length': sentinel.max_length
        }
    ),
    (
        MagicMock(
            action=sentinel.mode,
            encryption_context=None,
            algorithm=None,
            frame_length=None,
            max_length=None
        ),
        {
            'materials_manager': sentinel.materials_manager,
            'mode': sentinel.mode,
        }
    ),
    (
        MagicMock(
            action=sentinel.mode,
            encryption_context=sentinel.encryption_context,
            algorithm='AES_256_GCM_IV12_TAG16_HKDF_SHA384_ECDSA_P384',
            frame_length=sentinel.frame_length,
            max_length=None
        ),
        {
            'materials_manager': sentinel.materials_manager,
            'mode': sentinel.mode,
        }
    ),
    (
        MagicMock(
            action='encrypt',
            encryption_context=sentinel.encryption_context,
            algorithm='AES_256_GCM_IV12_TAG16_HKDF_SHA384_ECDSA_P384',
            frame_length=sentinel.frame_length,
            max_length=None
        ),
        {
            'materials_manager': sentinel.materials_manager,
            'mode': 'encrypt',
            'encryption_context': sentinel.encryption_context,
            'algorithm': aws_encryption_sdk.Algorithm.AES_256_GCM_IV12_TAG16_HKDF_SHA384_ECDSA_P384,
            'frame_length': sentinel.frame_length,
        }
    ),
    (
        MagicMock(
            action='encrypt',
            encryption_context=None,
            algorithm='AES_256_GCM_IV12_TAG16_HKDF_SHA384_ECDSA_P384',
            frame_length=sentinel.frame_length,
            max_length=None
        ),
        {
            'materials_manager': sentinel.materials_manager,
            'mode': 'encrypt',
            'algorithm': aws_encryption_sdk.Algorithm.AES_256_GCM_IV12_TAG16_HKDF_SHA384_ECDSA_P384,
            'frame_length': sentinel.frame_length,
        }
    ),
    (
        MagicMock(
            action='encrypt',
            encryption_context=sentinel.encryption_context,
            algorithm=None,
            frame_length=sentinel.frame_length,
            max_length=None
        ),
        {
            'materials_manager': sentinel.materials_manager,
            'mode': 'encrypt',
            'encryption_context': sentinel.encryption_context,
            'frame_length': sentinel.frame_length
        }
    ),
    (
        MagicMock(
            action='encrypt',
            encryption_context=sentinel.encryption_context,
            algorithm='AES_256_GCM_IV12_TAG16_HKDF_SHA384_ECDSA_P384',
            frame_length=None,
            max_length=None
        ),
        {
            'materials_manager': sentinel.materials_manager,
            'mode': 'encrypt',
            'encryption_context': sentinel.encryption_context,
            'algorithm': aws_encryption_sdk.Algorithm.AES_256_GCM_IV12_TAG16_HKDF_SHA384_ECDSA_P384
        }
    )
))
def test_stream_kwargs_from_args(args, stream_args):
    assert aws_encryption_sdk_cli.stream_kwargs_from_args(args, sentinel.materials_manager) == stream_args


@pytest.fixture
def patch_for_cli(mocker):
    mocker.patch.object(aws_encryption_sdk_cli, 'parse_args')
    aws_encryption_sdk_cli.parse_args.return_value = MagicMock(
        version=False,
        verbosity=sentinel.verbosity,
        quiet=sentinel.quiet,
        master_keys=sentinel.master_keys,
        caching=sentinel.caching_config,
        input=sentinel.input,
        output=sentinel.output,
        recursive=sentinel.recursive,
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite,
        suffix=sentinel.suffix
    )
    mocker.patch.object(aws_encryption_sdk_cli, 'setup_logger')
    mocker.patch.object(aws_encryption_sdk_cli, 'build_crypto_materials_manager_from_args')
    aws_encryption_sdk_cli.build_crypto_materials_manager_from_args.return_value = sentinel.crypto_materials_manager
    mocker.patch.object(aws_encryption_sdk_cli, 'stream_kwargs_from_args')
    aws_encryption_sdk_cli.stream_kwargs_from_args.return_value = sentinel.stream_args
    mocker.patch.object(aws_encryption_sdk_cli, 'process_cli_request')


def test_cli(patch_for_cli):
    test = aws_encryption_sdk_cli.cli(sentinel.raw_args)

    aws_encryption_sdk_cli.parse_args.assert_called_once_with(sentinel.raw_args)
    aws_encryption_sdk_cli.setup_logger.assert_called_once_with(
        sentinel.verbosity,
        sentinel.quiet
    )
    aws_encryption_sdk_cli.build_crypto_materials_manager_from_args.assert_called_once_with(
        key_providers_config=sentinel.master_keys,
        caching_config=sentinel.caching_config
    )
    aws_encryption_sdk_cli.stream_kwargs_from_args.assert_called_once_with(
        aws_encryption_sdk_cli.parse_args.return_value,
        sentinel.crypto_materials_manager
    )
    aws_encryption_sdk_cli.process_cli_request.assert_called_once_with(
        stream_args=sentinel.stream_args,
        source=sentinel.input,
        destination=sentinel.output,
        recursive=sentinel.recursive,
        interactive=sentinel.interactive,
        no_overwrite=sentinel.no_overwrite,
        suffix=sentinel.suffix
    )
    assert test is None


def test_cli_local_error(patch_for_cli):
    aws_encryption_sdk_cli.process_cli_request.side_effect = AWSEncryptionSDKCLIError(sentinel.error_message)
    test = aws_encryption_sdk_cli.cli()

    assert test is sentinel.error_message


def test_cli_unknown_error(patch_for_cli):
    aws_encryption_sdk_cli.process_cli_request.side_effect = Exception()
    test = aws_encryption_sdk_cli.cli()

    assert test.startswith('Encountered unexpected ')
