from google.appengine.api import users
from google.appengine.api import memcache
from datetime import *
import time
import re

from bo import *
from database.bubble import *
from database.person import *
from database.feedback import *
from database.zimport.zoin import *
from database.zimport.zbubble import *


class Dokumendid(boRequestHandler):
    def get(self):
        taskqueue.Task(url='/update/docs').add()

    def post(self):
        csv = []
        for c in db.Query(Counter).order('__key__').fetch(1000):
            for b in db.Query(Bubble).filter('registry_number_counter', c.key()).fetch(1000):
                if len(getattr(b, 'optional_bubbles', [])) > 0:
                    for sb in Bubble().get(b.optional_bubbles):
                        if sb:
                            csv.append('%s;%s;%s;%s;%s' % (c.displayname, sb.type, sb.key().id(), getattr(sb, 'registry_number', ''), sb.displayname))

        SendMail(
            to = 'argo.roots@artun.ee',
            subject = 'Docs',
            message = 'jee',
            attachments = [('Docs.csv', '\n'.join(csv))],
        )


class MemCacheInfo(boRequestHandler):
    def get(self):
        self.header('Content-Type', 'text/plain; charset=utf-8')

        if self.request.get('flush', '').lower() == 'true':
            memcache.flush_all()

        for k, v in memcache.get_stats().iteritems():
            if k in ['bytes', 'byte_hits']:
                v = '%skB' % (v/1024)
            if k == 'oldest_item_age':
                v = '%smin' % (v/60)
            self.echo('%s: %s' % (k, v))


class FixStuff(boRequestHandler):
    def get(self):
        self.header('Content-Type', 'text/plain; charset=utf-8')
        # taskqueue.Task(url='/update/stuff').add()

        bt = db.Query(Bubble).filter('path', 'person').get()
        b = Bubble().get('agpzfmJ1YmJsZWR1cg8LEgZCdWJibGUYy_rLAgw')
        b.x_type = bt.key()
        b.put()

    def post(self):
        pass


class FixRelations(boRequestHandler): # BubbleRelation to Bubble.x_br_...
    def get(self, type):
        taskqueue.Task(url='/update/relations/%s' % type).add()
        self.echo(str(db.Query(BubbleRelation).filter('type', type).filter('x_is_deleted', False).count(limit=100000)))
        self.echo(str(db.Query(BubbleRelation).filter('type', type).filter('x_is_deleted', True).count(limit=100000)))

    def post(self, type):
        rc = 0
        limit = 500
        step = int(self.request.get('step', 1))
        offset = int(self.request.get('offset', 0))

        for br in db.Query(BubbleRelation).filter('type', type).filter('x_is_deleted', False).order('__key__').fetch(limit=limit, offset=offset):
            rc += 1
            try:
                bubble = br.bubble
                setattr(bubble, 'x_br_%s' % type, MergeLists(getattr(bubble, 'x_br_%s' % type, []), br.related_bubble.key()))
                bubble.put()
            except:
                pass
        logging.debug('#' + str(step) + ' - ' + type + ' - ' + str(rc) + ' rows from ' + str(offset))

        if rc == limit:
            taskqueue.Task(url='/update/relations/%s' % type, params={'offset': (offset + rc), 'step': (step + 1)}).add()


class FixRelations2(boRequestHandler): #Change Person keys from Bubble.x_br_... to Bubble keys
    def get(self, bubbletype, relationtype):
        taskqueue.Task(url='/update/relations2/%s/%s' % (bubbletype, relationtype)).add()
        self.echo(str(db.Query(Bubble).filter('type', bubbletype).filter('x_is_deleted', False).count(limit=100000)))
        self.echo(str(db.Query(Bubble).filter('type', bubbletype).filter('x_is_deleted', True).count(limit=100000)))

    def post(self, bubbletype, relationtype):
        rc = 0
        limit = 200
        step = int(self.request.get('step', 1))
        offset = int(self.request.get('offset', 0))

        for bubble in db.Query(Bubble).filter('type', bubbletype).order('__key__').fetch(limit=limit, offset=offset):
            rc += 1
            for r in getattr(bubble, 'x_br_%s' % relationtype, []):
                p = db.get(r)
                if p.kind() == 'Person':
                    if hasattr(p, 'person2bubble'):
                        setattr(bubble, 'x_br_%s' % relationtype, MergeLists(getattr(bubble, 'x_br_%s' % relationtype, []), p.person2bubble))
                        bubble.put()

        logging.debug('#' + str(step) + ' - ' + bubbletype + ' - ' + relationtype + ' - ' + str(rc) + ' rows from ' + str(offset))

        if rc == limit:
            taskqueue.Task(url='/update/relations2/%s/%s' % (bubbletype, relationtype), params={'offset': (offset + rc), 'step': (step + 1)}).add()


def main():
    Route([
            ('/update/docs', Dokumendid),
            ('/update/cache', MemCacheInfo),
            ('/update/stuff', FixStuff),
            (r'/update/relations/(.*)', FixRelations),
            (r'/update/relations2/(.*)/(.*)', FixRelations2),
        ])


if __name__ == '__main__':
    main()
