# Monitor Selector

Work From Home?
Have a Windows PC and a work laptop/computer?
Not trying to purchase an expensive KVM that supports high refresh rates and complicated peripherals?

Here's a simple tool to select monitor input source.

This is best paired with a USB switch to toggle peripherals between the two computers.

I created a sample batch file to toggle between work and personal profiles, then I used iCue to assign
a macro to the batch file (fn + s).

## Build

### Pre-req windows

py3.12
poetry
```bash
pipx install poetry
poetry --version
```

https://scoop.sh/
https://pipx.pypa.io/stable/installation/


### Local Run

```bash
# list sources
poetry run python main.py --list

# Set
poetry run python main.py --set 1=HDMI1 2=DP1

# Toggle between work and personal profiles
poetry run python main.py --toggle
```

# Maintenance

```bash
poetry run isort .
poetry run black .
```