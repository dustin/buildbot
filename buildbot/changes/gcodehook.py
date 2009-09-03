# gcodehook.py - Google Code webhook for buildbot
#
# Copyright 2009 Nicolas Alvarez <nicolas.alvarez@gmail.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, version 2 or later, incorporated herein by
# reference.

from buildbot.changes import base, changes
from twisted.web import server, resource
from twisted.application import strports
from twisted.python import log

import simplejson

def bbotChangeFromHookData(revision):
    files = []
    files.extend(revision['added'])
    files.extend(revision['modified'])
    files.extend(revision['removed'])
    return changes.Change(
        who = revision['author'],
        files = files,
        comments = revision['message'],
        revision = revision['revision'],
        revlink = revision['url'],
        when = revision['timestamp']
    )

class HookHandler(resource.Resource):
    """
    This class handles a web hook request from Google Code, following the spec in:
    http://code.google.com/p/support/wiki/PostCommitWebHooks
    """
    isLeaf = True

    def __init__(self, addChangeFunc):
        resource.Resource.__init__(self)
        self.addChange = addChangeFunc

    def render_GET(self, req):
        req.setHeader("Content-Type", "text/plain")
        return "This is a Google Code commit hook handler.\n"

    def render_POST(self, req):
        try:
            # req.content is not documented in twisted API;
            # not sure if I can rely on it
            data = simplejson.load(req.content)
        except ValueError, e:
            req.setResponseCode(400)
            return "Couldn't parse JSON data. Error message: %s" % e.message

        for revision in data["revisions"]:
            change = bbotChangeFromHookData(revision)
            self.addChange(change)

        req.setResponseCode(200)
        req.setHeader("Content-Type", "text/plain")
        return "Success.\n"


class GoogleCodeHook(base.ChangeSource):
    """
    TODO
    """
    def __init__(self, http_port=None):
        if type(http_port) is int:
            http_port = "tcp:%d" % http_port
        self.http_port = http_port

        self.handler = resource.Resource()
        self.handler.putChild("gcode-hook", HookHandler(self.addChange))
        self.site = server.Site(self.handler)
        self.websrv = strports.service(self.http_port, self.site)

    def startService(self):
        self.websrv.startService()
        base.ChangeSource.startService(self)

    def stopService(self):
        self.websrv.stopService()
        base.ChangeSource.stopService(self)

    def addChange(self, change):
        log.msg("addChange called")
        self.parent.addChange(change)

