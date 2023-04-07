
class User:

    def __init__(self, username, socket, state=None, friends=None, pending_friends=None, pending_files=None):
        self._username = username
        self._socket = socket

        if state is None:
            self._state = 'chatting'
        else:
            self._state = state

        if friends is None:
            self._friends = []
        else:
            self._friends = friends

        if pending_friends is None:
            self._pending_friends = []
        else:
            self._pending_friends = pending_friends

        if pending_files is None:
            self._pending_files = []
        else:
            self._pending_files = pending_files

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        self._username = value

    @property
    def socket(self):
        return self._socket

    @socket.setter
    def socket(self, value):
        self._socket = value

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def friends(self):
        return self._friends

    @friends.setter
    def friends(self, value):
        self._friends = value

    def add_friends(self, value):
        self._friends.append(value)

    def remove_friends(self, value):
        self._friends.remove(value)

    @property
    def pending_friends(self):
        return self._pending_friends

    @pending_friends.setter
    def pending_friends(self, value):
        self._pending_friends = value

    def add_pending_friends(self, value):
        self._pending_friends.append(value)

    def remove_pending_friends(self, value):
        self._pending_friends.remove(value)

    @property
    def pending_files(self):
        return self._pending_files

    @pending_files.setter
    def pending_files(self, value):
        self._pending_files = value

    def add_pending_files(self, value):
        self._pending_files.append(value)

    def remove_pending_files(self, value):
        self._pending_files.remove(value)



