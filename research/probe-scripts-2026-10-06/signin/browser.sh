#!/bin/sh
printf '%s\n' "$1" > "<this folder>/url.tmp" && mv "<this folder>/url.tmp" "<this folder>/url"
