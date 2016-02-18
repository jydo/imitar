# Imitar

*A framework for emulating AV Devices*

## Overview

Imitar is a framework and set of tools for emulating AV device protocols for devices such as Matrix Switchers, Projectors, Lighting systems, and more. It was created in order to ease the burden of programming AV control systems when hardware access is limited. Imitar can also be used to create integration tests for your AV programs allowing you to ensure that your clients are receiving the highest quality code.

Imitar was written to emulate device protocols, which means that it is fully compatible with all major control systems manufacturers such as Crestron, AMX, Control4, and Savant. It is Apache 2 licensed, which means you can use it for personal and commercial projects at no cost.

Imitar comes bundled with a few emulators out of the box, but also includes the framework to easily create new ones. Contributions are welcome and encouraged.

## Versioning

Imitar uses semantic versioning, all releases will follow a `Major.Minor.Patch` versioning scheme. In short:

* Changes that break backwards compatibility will bump the `Major` version number.
* Changes that add new features without breaking backwards compatibility will bump the `Minor` version number.
* Changes that fix a bug will bump the `Patch` version number.

## Contributing

If you'd like to contribute a new emulator, or improve the framework simply fork the repository, add your changes, and create a pull request. Contributions should include unit tests written with the PyTest framework.

## License

Copyright © 2016 Jydo inc.

Released under The Apache 2 license, see the `LICENSE` file for details
