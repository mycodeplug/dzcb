"""
dzcb.exceptions - errors that may be raised
"""


class InvalidDmrID(ValueError):
    pass


class DuplicateDmrID(ValueError):
    def __init__(self, msg, existing_contact):
        super().__init__(msg)
        self.existing_contact = existing_contact
