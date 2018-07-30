"""
Provides utility methods.
"""

import os
import logging
import zipfile
import tarfile

from . import getconfig


logger = logging.getLogger()


def validate_credentials(request):
    """Returns if the authorization headers are valid.

    :param werkzeug.wrappers.BaseRequest request:
    :return: True if authorization headers are valid - otherwise False.
    """
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    return username == getconfig.username and password == getconfig.password


class UploadedFile(object):
    """
    UploadedFile represents a file uploaded during a POST request.
    """

    def __init__(self, filename, stream):
        """Instantiate an UploadedFile

        :param str filename: The name of the file.
        :param stream: The open file stream.
        """
        self._filename = filename
        self._stream = stream

    @classmethod
    def from_request(cls, request):
        """
        Instantiate an UploadedFile from the first file in a request.

        :param werkzeug.wrappers.BaseRequest request: The POST request.
        :return: The instantiated UploadedFile.
        :raises ValueError: if no files exist within the request.
        """
        uploaded_files = list(request.files.values())
        if len(uploaded_files) > 1:
            logger.warning(
                'Only one file can be uploaded for each request. '
                'Only the first file will be used.'
            )
        elif len(uploaded_files) == 0:
            raise ValueError('Request does not contain uploaded file')

        current_file = uploaded_files[0]
        return cls(current_file.filename, current_file.stream)

    def get_filename(self):
        return self._filename

    def get_stream(self):
        return self._stream

    def close(self):
        """close the file stream
        """
        try:
            self._stream.close()
        except:
            pass


class FileExpander(object):
    """
    Manager for exanding compressed project files.

    It automatically detects the compression method and allocates
    the right handler.

    Currently the supported methods are:
    - zip
    - tar
    """

    ZIP_EXTENSIONS = ('.zip', )
    TAR_EXTENSIONS = ('.tar', '.tgz', '.tar.gz', '.tar.bz2')

    def __init__(self, uploaded_file):
        self._file = uploaded_file
        self._handle = None

    @classmethod
    def detect_compression_method(cls, filename):
        """
        Attempt to detect the compression method from the filename extension.

        :param str extension: The file extension.
        :return: The compression method ('zip' or 'tar').
        :raises ValueError: If fails to detect the compression method.
        """
        if any(filename.endswith(ext) for ext in cls.ZIP_EXTENSIONS):
            return 'zip'
        if any(filename.endswith(ext) for ext in cls.TAR_EXTENSIONS):
            return 'tar'

        raise ValueError('Unknown compression method for %s' % filename)

    def __enter__(self):
        method = self.detect_compression_method(self._file.get_filename())
        if method == 'zip':
            self._handle = zipfile.ZipFile(self._file.get_stream())
        elif method == 'tar':
            self._handle = tarfile.open(fileobj=self._file.get_stream(), mode='r:*')
        else:
            raise ValueError('Unsupported method %s' % method)

        return self._handle

    def __exit__(self, exc_type, exc_value, traceback):
        self._handle.close()
