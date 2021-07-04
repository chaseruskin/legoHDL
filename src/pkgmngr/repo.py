#the link between the registry communicating with capsules (packages)
class Repo:
    def __init__(self, l_a, lib, name, l_v, g_url, l_path, m_b='master'):
        self.last_activity = l_a
        self.library = lib
        self.name = name
        self.last_version = l_v
        self.m_branch = m_b
        self.downloaded = False
        self.git_url = g_url
        self.local_path = l_path
        pass
    pass
