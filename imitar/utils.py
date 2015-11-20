# Copyright 2015 jydo inc. All rights reserved.
from threading import Thread
import time


def run_later(fn, seconds):
    def later():
        time.sleep(seconds)
        fn()

    Thread(target=later, daemon=True).start()
