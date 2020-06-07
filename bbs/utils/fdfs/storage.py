from fdfs_client.client import Fdfs_client
from django.core.files.storage import Storage
from django.conf import settings


class FDFSStorage(Storage):
    '''FDFS存储类'''
    def __init__(self, conf_path=None, server_url=None):
        if conf_path is None:
            conf_path = settings.FDFS_CLIENT_CONFIG
        self.conf_path = conf_path

        if server_url is None:
            server_url = settings.FDFS_SERVER_URL
        self.server_url = server_url

    def _open(self, name, mode='rb'):
        '''打开文件时执行'''
        pass

    def _save(self, name, content):
        '''存储: name-文件名; content-File对象'''
        # 创建fdfs的实例对象
        client = Fdfs_client(self.conf_path)

        # 上传文件
        result = client.upload_by_buffer(content.read())

        if result.get('Status') != 'Upload successed.':
            raise Exception('上传文件到FDFS失败')

        # 返回文件id
        filename = result.get('Remote file_id')
        return filename

    def exists(self, name):
        return False

    def url(self, name):
        return self.server_url+name