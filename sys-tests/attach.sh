#!/bin/bash

set -xe

uvx awusb attach --serial 000001
uvx awusb attach --serial FTA955HH
uvx awusb attach --serial FTA94JXC
uvx awusb attach --serial FTA974AY
uvx awusb attach --serial 0019C52F
uvx awusb attach --serial 0000000000000001
uvx awusb attach --desc Unifying
uvx awusb attach --desc Scope
uvx awusb attach --desc WebCam
