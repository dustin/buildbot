"""A LatentSlave that starts VirtualBox-based virtual machines on demand.


"""
# Copyright (C) 2009 Nicolas Alvarez <nicolas.alvarez@gmail.com>

import time

from vboxapi import VirtualBoxManager

from buildbot.buildslave import AbstractLatentBuildSlave
from twisted.internet import threads, defer
from twisted.python import log

manager = None

def bootVM(uuid):
    global manager
    if manager is None:
        manager = VirtualBoxManager(None, None)
    vbox = manager.vbox

    log.msg("requested to boot VM %s" % uuid)

    session = manager.mgr.getSessionObject(vbox)

    progress = vbox.openRemoteSession(session, uuid, "vrdp", "")
    log.msg("Starting remote VBox session")
    try:
        progress.waitForCompletion(-1)

        if not progress.completed:
            raise RuntimeError("What the hell?")
        rc = int(progress.resultCode)
        log.msg("Remote VBox session started")

        #return rc
    finally:
        session.close()

def shutdownVM(uuid):
    global manager
    if manager is None:
        manager = VirtualBoxManager(None, None)
    vbox = manager.vbox

    log.msg("Requested to shutdown VM %s" % uuid)

    session = manager.mgr.getSessionObject(vbox)

    vbox.openExistingSession(session, uuid)
    try:
        session.console.powerButton() # boop
        log.msg("powerButton pressed, waiting for VM to shut down")

        while session.console.state != manager.constants.MachineState_PoweredOff:
            time.sleep(1)
        log.msg("MachineState = PoweredOff")
    finally:
        if session.state != manager.constants.SessionState_Closed:
            session.close()

class VBoxBuildSlave(AbstractLatentBuildSlave):
    def __init__(self, name, password, uuid, max_builds=None, notify_on_missing=[], missing_timeout=60*10, build_wait_timeout=60*10, properties={}):
        AbstractLatentBuildSlave.__init__(
            self, name, password, max_builds, notify_on_missing,
            missing_timeout, build_wait_timeout, properties)
        self.uuid = uuid

    def start_instance(self):
        return threads.deferToThread(bootVM, self.uuid)

    def stop_instance(self, fast):
        return threads.deferToThread(shutdownVM, self.uuid)

