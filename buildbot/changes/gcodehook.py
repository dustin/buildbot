# gcodehook.py - Google Code webhook for buildbot
#
# Copyright 2009 Nicolas Alvarez <nicolas.alvarez@gmail.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, version 2 or later, incorporated herein by
# reference.

from buildbot.changes import base, changes, svnpoller
from twisted.web import server, resource
from twisted.application import strports
from twisted.python import log

import simplejson

class HookHandler(resource.Resource):
    """
    This class handles a web hook request from Google Code, following the spec in:
    http://code.google.com/p/support/wiki/PostCommitWebHooks
    """
    isLeaf = True

    def __init__(self, gotChangesFunc):
        resource.Resource.__init__(self)
        self.gotChanges = gotChangesFunc

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

        f = getattr(self, "gotChanges")
        f(data["revisions"])


        req.setResponseCode(200)
        req.setHeader("Content-Type", "text/plain")
        return "Success.\n"


class GoogleCodeHook(base.ChangeSource):
    """
    TODO

    split_file: a function that is called with a string of the form
    (BRANCH)/(FILEPATH) and should return a tuple (BRANCH, FILEPATH). This
    function should match your repository's branch-naming policy. Each changed
    file has a fully-qualified URL that can be split into a prefix (which equals
    the value of the 'svnurl' argument) and a suffix; it is this suffix which is
    passed to the split_file function.

    If the function returns None, the file is ignored. Use this to indicate
    that the file is not a part of this project.

    Useful implementations of split_file functions are available in the
    svnpoller module.

    The default of split_file= is None, which indicates that no splitting should
    be done. This is equivalent to the following function::

     return (None, path)
    """
    def __init__(self, http_port=None, split_file=None):
        if type(http_port) is int:
            http_port = "tcp:%d" % http_port
        self.http_port = http_port

        self.handler = HookHandler(self.gotChanges)
        self.split_file_function = split_file or svnpoller.split_file_alwaystrunk
        self.createWebServer(self.http_port, self.handler)

    def split_file(self, path):
        # use getattr() to avoid turning this function into a bound method,
        # which would require it to have an extra 'self' argument
        f = getattr(self, "split_file_function")
        return f(path)

    def createWebServer(self, http_port, handler):
        self.root_handler = resource.Resource()
        self.root_handler.putChild("gcode-hook", HookHandler(self.gotChanges))
        self.site = server.Site(self.root_handler)
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

    def gotChanges(self, revisions):
        for revision in revisions:
            for change in self.changesFromHookData(revision):
                self.addChange(change)

    def changesFromHookData(self, revision):
        files = []
        files.extend(revision['added'])
        files.extend(revision['modified'])
        files.extend(revision['removed'])
        branches = {}

        for file in files:
            if len(file) > 0 and file[0] == '/':
                file = file[1:]
            where = self.split_file(file)
            if where:
                branch, filename = where
                if not branch in branches:
                    branches[branch] = {'files':[]}
                branches[branch]['files'].append(filename)

        for branch in branches.keys():
            yield changes.Change(
                who = revision['author'],
                files = branches[branch]['files'],
                branch = branch,
                comments = revision['message'],
                revision = revision['revision'],
                revlink = revision['url'],
                when = revision['timestamp']
            )

