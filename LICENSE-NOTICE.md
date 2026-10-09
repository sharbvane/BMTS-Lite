# License Notice

The BMTS Lite source at this revision and later is licensed under the GNU
Affero General Public License, version 3 only (AGPL-3.0-only). Copyright
(C) 2026 Cui (sharbvane). See [LICENSE](LICENSE) for the complete terms.

This change applies to the current source revision and later revisions. It
does not rewrite repository history or change the terms attached to any
previously distributed snapshot or release; those copies remain under the
license that accompanied them.

No third-party media or source code is vendored for the OpenMontage adapter.
The separately installed Python packages and FFmpeg executable retain their
respective upstream licenses and notices. Direct Python runtime dependencies
are listed in [requirements-runtime.txt](requirements-runtime.txt).

The direct runtime package licenses are permissive or compatible copyleft:
librosa (ISC), NumPy and SciPy (BSD-3-Clause), OpenCV (Apache-2.0), and
SoundFile (BSD-3-Clause). Package wheels may include additional native
components under their own licenses; retain the notices supplied with those
distributions. The OpenMontage adapter does not redistribute these packages or
FFmpeg.
