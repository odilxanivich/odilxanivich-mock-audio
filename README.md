# odilxanivich-mock-audio

Audio recordings for the Odilxanivich in Korea Mock Arena. Served to the website through the jsDelivr CDN.

## Folder layout

```
ielts/
  odilxanivich-1-listening-section-1.mp3
  odilxanivich-1-listening-section-2.mp3
  odilxanivich-1-listening-section-3.mp3
  odilxanivich-1-listening-section-4.mp3
tools/
  convert.sh   WAV/M4A -> small mono MP3 with the correct name
  check.sh     verifies files and URLs
```

File names follow `<test-id>-section-<n>.mp3`.

## Website setting (Vercel and .env.local)

```
NEXT_PUBLIC_MOCK_AUDIO_BASE=https://cdn.jsdelivr.net/gh/odilxanivich/odilxanivich-mock-audio@main/ielts/
```

## Updating a file

Replace the MP3, commit and push. jsDelivr caches files, so purge the old one:
`https://purge.jsdelivr.net/gh/odilxanivich/odilxanivich-mock-audio@main/ielts/<file>.mp3`

## Copyright

© Odilxanivich in Korea. All rights reserved. The recordings are for use on odilxanivichinkorea.com only.
# odilxanivich-mock-audio
