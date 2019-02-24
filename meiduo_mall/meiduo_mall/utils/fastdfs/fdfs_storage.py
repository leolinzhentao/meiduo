from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client

from django.conf import settings


class FastDFSStorage(Storage):
    """自定义文件存储系统"""
    def __init__(self, base_url=None, client_conf=None):
        """
        初始化方法
        :param base_url: storage ip:端口
        :param client_conf: fastdfd客户端配置文件
        """
        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

    def _open(self, name, mode='rb'):
        """打开文件，但是自定义文件存储系统的目的，只是为了上传和下载，所以此方法什么也不做，直接pass"""
        pass

    def _save(self, name, content):
        """
        上传图片时调用此方法
        :param name: 要上传的文件名
        :param content: 要上传的文件对象，将来可以通过content.read()读取到文件的二进制数据
        :return: 返回file_id,将来会自动存储到image字段
        """
        # 1.创建fdfs客户端
        # client = Fdfs_client('meiduo_mall/utils/fastdfs/client.conf')
        # client = Fdfs_client(settings.FDFS_CLIENT_CONF)
        client = Fdfs_client(self.client_conf)

        # 2.上传文件
        # client.upload_by_filename() 如果是要指定一个文件路径和文件名来上传文件用此方法， filename上传的文件是有后缀的
        ret = client.upload_by_buffer(content.read())  # 如果是通过文件数据的二进制来上传用buffer ， 这个方法上传的文件是没有后缀的

        # 3.安全判断
        if ret.get('Status') != 'Upload successed.':
            raise Exception('upload file failed')

        # 4.返回file_id
        return ret.get('Remote file_id')

    def exists(self, name):
        """
        判断要上传的文件是否已存在，如果存在就不上传了，不存在再调用save方法上传
        :param name: 要进行判断上不上传的文件名
        :return: True或False如果返回False 表示此文件不存在，就上传，如果返回True表示文件已存在就不上传
        """
        return False

    def url(self, name):
        """
        当访问image 字段的url属性时，就会自动调用此url方法拼接好文件的完整url路径
        :param name: 是当初save方法中返回的file_id
        :return: storage ip:端口 + file_id
        """
        return self.base_url + name

