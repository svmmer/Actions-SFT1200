#!/bin/bash
#
# Copyright (c) 2019-2020 P3TERX <https://p3terx.com>
#
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#
# https://github.com/P3TERX/Actions-OpenWrt
# File name: diy-part1.sh
# Description: OpenWrt DIY script part 1 (Before Update feeds)
#

set -euo pipefail

REPO_ROOT="${GITHUB_WORKSPACE:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
SOURCE_LOCK_FILE="${SOURCE_LOCK_FILE:-$REPO_ROOT/sources.lock}"
python3 "$REPO_ROOT/scripts/source-lock.py" validate "$SOURCE_LOCK_FILE"
# shellcheck source=/dev/null
source "$SOURCE_LOCK_FILE"

# These small compatibility rules are vendored from LEDE_REV and
# OPENSSL_ENGINE_ORIGIN_REV so a branch change or unavailable raw-file host
# cannot alter the production build.
install -m 0644 "$REPO_ROOT/build-support/meson.mk" ./include/meson.mk
install -m 0644 "$REPO_ROOT/build-support/openssl-engine.mk" ./include/openssl-engine.mk

# Replace any previous custom definitions so repeated local runs cannot leave
# a floating source or a duplicate feed behind.
sed -i -E \
  '/^src-git(-full)? (packages|luci|routing|telephony|gl|luci2|packages2|PWpackages|PWluci|helloworld) /d' \
  feeds.conf.default

# The legacy feeds script treats URL^SHA as a detached immutable checkout.
# Do not combine ;branch and ^revision: branch parsing takes precedence.
{
  echo "src-git packages ${BASE_PACKAGES_REPO}^${BASE_PACKAGES_REV}"
  echo "src-git luci ${BASE_LUCI_REPO}^${BASE_LUCI_REV}"
  echo "src-git routing ${BASE_ROUTING_REPO}^${BASE_ROUTING_REV}"
  echo "src-git telephony ${BASE_TELEPHONY_REPO}^${BASE_TELEPHONY_REV}"
  echo "src-git gl ${GL_FEED_REPO}^${GL_FEED_REV}"
  echo "src-git luci2 ${LUCI2_REPO}^${LUCI2_REV}"
  echo "src-git packages2 ${PACKAGES2_REPO}^${PACKAGES2_REV}"
  echo "src-git PWpackages ${PWPACKAGES_REPO}^${PWPACKAGES_REV}"
  echo "src-git PWluci ${PASSWALL_REPO}^${PASSWALL_REV}"
  echo "src-git helloworld ${HELLOWORLD_REPO}^${HELLOWORLD_REV}"
} >> feeds.conf.default

./scripts/feeds clean
