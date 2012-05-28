from tornado import database
from tornado.options import options

import logging
import hashlib

from collections import defaultdict


def formatDatetime(d, format='%(day)d.%(month)d.%(year)d %(hour)d:%(minute)d'):
    """
        Formats and returns date as string. Format:
        %%(day)d
        %%(month)d
        %%(year)d
        %%(hour)d
        %%(minute)d
    """
    return format % {'year': d.year, 'month': d.month, 'day': d.day, 'hour': d.hour, 'minute': d.minute}


class myDb():
    """
    Main database class. All database actions should go thru this.

    """
    def __init__(self, language='estonian'):
        self.language = language

    @property
    def db(self):
        return database.Connection(
            host        = options.mysql_host,
            database    = options.mysql_database,
            user        = options.mysql_user,
            password    = options.mysql_password,
        )

    def getBubbleList(self, bubble_id=None, search=None, only_public=True, bubble_definition=None, user_id=None, limit=None):
        return self.getBubbleProperties(bubble_id=self.getBubbleIdList(bubble_id=bubble_id, search=search, only_public=only_public, bubble_definition=bubble_definition, user_id=user_id, limit=limit), only_public=only_public)

    def getBubbleIdList(self, bubble_id=None, search=None, only_public=True, bubble_definition=None, user_id=None, limit=None):
        """
        Get list of Bubble IDs. bubble_id, bubble_definition and user_id can be single ID or list of IDs.

        """
        sql = 'SELECT STRAIGHT_JOIN DISTINCT bubble.id AS id FROM property_definition, property, bubble, relationship WHERE property.property_definition_id = property_definition.id AND bubble.id = property.bubble_id AND relationship.bubble_id = bubble.id'
        if bubble_id:
            if type(bubble_id) is not list:
                bubble_id = [bubble_id]
            sql += ' AND bubble.id IN (%s)' % ','.join(map(str, bubble_id))

        if search:
            for s in search.split(' '):
                sql += ' AND value_string LIKE \'%%%%%s%%%%\'' % s

        if only_public == True:
            sql += ' AND property_definition.public = 1 AND bubble.public = 1'

        if bubble_definition:
            if type(bubble_definition) is not list:
                bubble_definition = [bubble_definition]
            sql += ' AND bubble.bubble_definition_id IN (%s)' % ','.join(map(str, bubble_definition))

        if user_id:
            if type(user_id) is not list:
                user_id = [user_id]
            sql += ' AND relationship.related_bubble_id IN (%s) AND relationship.type IN (\'viewer\', \'editor\', \'owner\')' % ','.join(map(str, user_id))

        sql += ' ORDER BY bubble.id'

        if limit:
            sql += ' LIMIT %d' % limit

        sql += ';'
        logging.info(sql)

        items = self.db.query(sql)
        if not items:
            return []
        return [x.id for x in items]

    def getBubbleProperties(self, bubble_id, only_public=True):
        """
        Get Bubble Properties. bubble_id can be single ID or list of IDs.

        """
        if not bubble_id:
            return []

        if type(bubble_id) is not list:
            bubble_id = [bubble_id]

        if only_public == True:
            public = 'AND property_definition.public = 1 AND bubble.public = 1'
        else:
            public = ''

        sql = """
            SELECT
            bubble_definition.id AS bubble_definition_id,
            bubble.id AS bubble_id,
            property_definition.id AS property_definition_id,
            property.id AS property_id,

            bubble.created AS bubble_created,

            bubble_definition.%(language)s_label AS bubble_label,
            bubble_definition.%(language)s_label_plural AS bubble_label_plural,
            bubble_definition.%(language)s_description AS bubble_description,

            property_definition.%(language)s_fieldset AS property_fieldset,
            property_definition.%(language)s_label AS property_label,
            property_definition.%(language)s_label_plural AS property_label_plural,
            property_definition.%(language)s_description AS property_description,

            property.id AS property_id,
            property.value_string AS value_string,
            property.value_text AS value_text,
            property.value_integer AS value_integer,
            property.value_decimal AS value_decimal,
            property.value_boolean AS value_boolean,
            property.value_datetime AS value_datetime,
            property.value_reference AS value_reference,
            property.value_file AS value_file,
            property_definition.datatype AS property_datatype,
            property_definition.dataproperty AS property_dataproperty,
            property_definition.multiplicity AS property_multiplicity,
            property_definition.ordinal AS property_ordinal

            FROM
            bubble,
            bubble_definition,
            property,
            property_definition

            WHERE property.bubble_id = bubble.id
            AND bubble_definition.id = bubble.bubble_definition_id
            AND property_definition.id = property.property_definition_id
            AND bubble_definition.id = property_definition.bubble_definition_id
            AND (property.language = '%(language)s' OR property.language IS NULL)
            %(public)s
            AND bubble.id IN (%(idlist)s)
        """ % {'language': self.language, 'public': public, 'idlist': ','.join(map(str, bubble_id))}
        # logging.info(sql)

        items = {}
        for row in self.db.query(sql):
            if not row.value_string and not row.value_text and not row.value_integer and not row.value_decimal and not row.value_boolean and not row.value_datetime and not row.value_reference and not row.value_file:
                continue

            #Item
            items.setdefault('item_%s' % row.bubble_id, {})['id'] = row.bubble_id
            items.setdefault('item_%s' % row.bubble_id, {})['label'] = row.bubble_label
            items.setdefault('item_%s' % row.bubble_id, {})['description'] = row.bubble_description
            items.setdefault('item_%s' % row.bubble_id, {})['created'] = row.bubble_created

            #Property
            items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {})['id'] = row.property_id
            items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {})['label'] = row.property_label
            items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {})['description'] = row.property_description
            items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {})['datatype'] = row.property_datatype
            items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {})['dataproperty'] = row.property_dataproperty
            items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {})['multiplicity'] = row.property_multiplicity
            items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {})['ordinal'] = row.property_ordinal

            #Value
            if row.property_datatype in ['string', 'dictionary', 'dictionary_string', 'select', 'dictionary_select']:
                value = row.value_string
            elif row.property_datatype in ['text', 'dictionary_text']:
                value = row.value_text
            elif row.property_datatype == 'integer':
                value = row.value_integer
            elif row.property_datatype == 'float':
                value = row.value_decimal
            elif row.property_datatype == 'date':
                value = formatDatetime(row.value_datetime)
            elif row.property_datatype == 'datetime':
                value = formatDatetime(row.value_datetime)
            elif row.property_datatype in ['reference']:
                value = row.value_reference
            elif row.property_datatype in ['blobstore']:
                blobstore = self.db.get('SELECT id, filename, filesize FROM file WHERE id=%s', row.value_file)
                value = blobstore.filename
                items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {}).setdefault('values', {}).setdefault('value_%s' % row.property_id, {})['file_id'] = blobstore.id
                items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {}).setdefault('values', {}).setdefault('value_%s' % row.property_id, {})['filesize'] = blobstore.filesize
            elif row.property_datatype in ['boolean']:
                value = row.value_boolean
            elif row.property_datatype in ['counter']:
                value = row.value_reference
            else:
                value = 'X'

            items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {}).setdefault('values', {}).setdefault('value_%s' % row.property_id, {})['value'] = value
            items.setdefault('item_%s' % row.bubble_id, {}).setdefault('properties', {}).setdefault('%s' % row.property_dataproperty, {}).setdefault('values', {}).setdefault('value_%s' % row.property_id, {})['id'] = row.property_id

        return items.values()

    def getFile(self, file_id, only_public=True):
        """
        Returns file object. Properties are id, file, filename

        """
        if only_public == True:
            publicsql = 'AND property_definition.public = 1'
        else:
            publicsql = ''

        sql = """
            SELECT
            file.id,
            file.file,
            file.filename
            FROM
            file,
            property,
            property_definition
            WHERE property.value_file = file.id
            AND property_definition.id = property.property_definition_id
            AND file.id = %(file_id)s
            %(public)s
            LIMIT 1
            """ % {'file_id': file_id, 'public': publicsql}
        # logging.info(sql)

        return self.db.get(sql)

    def getBubbleImage(self, id):
        return 'http://www.gravatar.com/avatar/%s?d=identicon' % (hashlib.md5(str(id)).hexdigest())

    def getMenu(self, user_id):
        """
        Returns user menu

        """

        sql = """
            SELECT DISTINCT
            bubble_definition.id,
            bubble_definition.%(language)s_menu AS menugroup,
            bubble_definition.%(language)s_label AS item
            FROM
            bubble_definition,
            bubble,
            relationship
            WHERE bubble.bubble_definition_id = bubble_definition.id
            AND relationship.bubble_id = bubble.id
            AND relationship.type IN ('viewer', 'editor', 'owner')
            AND bubble_definition.estonian_menu IS NOT NULL
            AND relationship.related_bubble_id = %(user_id)s
            ORDER BY
            bubble_definition.estonian_menu,
            bubble_definition.estonian_label;
        """ % {'language': self.language, 'user_id': user_id}
        # logging.info(sql)

        menu = {}
        for m in self.db.query(sql):
            menu.setdefault(m.menugroup, []).append({'id': m.id, 'title': m.item})
        return menu


class dBubble():
    """docstring for dBubble"""
    def __init__(self, id):
        self.id = id
        self.PropertyDefinitions = {}

    def setProperty(self, tuple, language=None):
        (property_key, property_value) = tuple
        retrun False if not self.loadPropertyDefinitions()
        return False if not self.PropertyDefinitions['property_key']

        pd = self.PropertyDefinitions['property_key']
        setvalues = ['property_definition_id=%s' % pd.id]
        setvalues.append("value_%(valuetype)s='%(value)s'" % {'valuetype': pd.datatype, 'value': property_value})
        setvalues.append("language='%s'" % language) if language
        sql = "INSERT INTO property SET %s;" % u", ".join(setvalues)
        db = myDb().db
        logging.info(sql)
        db.execute(sql)
        db.close()

    def loadBubbleDefinition(self):
        return True if self.BubbleDefinition
        sql = 'SELECT bd.* FROM bubble AS b LEFT JOIN bubble_definition AS bd ON b.bubble_definition_id = bd.id WHERE b.id = %s;' % self.id
        logging.info(sql)
        self.BubbleDefinition = self.db.query(sql)
        return True

    def loadPropertyDefinitions(self):
        return True if self.PropertyDefinitions
        return False if not self.loadBubbleDefinition()
        sql = 'SELECT pd.* FROM property_definition AS pd WHERE pd.bubble_definition_id = %s;' % self.BubbleDefinition.id
        logging.info(sql)
        self.PropertyDefinitions = self.db.query(sql)
        return True
