from google.appengine.api import users
from google.appengine.ext import db

from bo import *
from database.zimport.zoin import *
from database.person import *


class zPerson(db.Expando):
    def zimport(self):
        p = GetZoin('Person', self.key().name())
        if not p:
            p = Person()

        if '@' in self.user:
            p.users = AddToList(self.user, p.users)
        p.forename = self.forename
        p.surname = self.surname
        p.idcode = self.idcode
        p.gender = self.gender
        p.birth_date = self.birth_date
        p.leecher = MergeLists(p.leecher, GetZoinKeyList('Bubble', self.leecher))
        p.seeder = MergeLists(p.leecher, GetZoinKeyList('Bubble', self.seeder))
        p.put('zimport')
        p.AutoFix()

        AddZoin(
            entity_kind = 'Person',
            old_key = self.key().name(),
            new_key = p.key(),
        )
        self.delete()


class zRole(db.Expando):
    def zimport(self):
        r = GetZoin('Role', self.key().name())
        if not r:
            r = Role()

        name = Dictionary(
            name = 'role_name',
            estonian = self.name_estonian,
            english = self.name_english
        ).put('zimport')

        r.name = name
        r.rights = StrToList(self.rights)
        r.put('zimport')

        AddZoin(
            entity_kind = 'Role',
            old_key = self.key().name(),
            new_key = r.key(),
        )
        self.delete()


class zPersonRole(db.Expando):
    def zimport(self):
        person = GetZoin('Person', self.person)
        role_key = GetZoinKey('Role', self.role)
        if person and role_key:
            person.roles = AddToList(role_key, person.roles)
            person.put('zimport')

        self.delete()


class zContact(db.Expando):
    def zimport(self):
        c = GetZoin('Contact', self.key().name())
        if not c:
            person = GetZoin('Person', self.person)
            c = Contact(parent=person)

        c.type = self.type
        c.value = self.value
        c.put('zimport')
        c.AutoFix()

        AddZoin(
            entity_kind = 'Contact',
            old_key = self.key().name(),
            new_key = c.key(),
        )
        self.delete()
