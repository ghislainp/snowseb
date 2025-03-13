# snowseb

A simple GUI-based software to teach snow surface energy budget.

Open a Campbell Scientific file containing micro-meteorological data (Tair, RH, Wind Speed, SWup, SWdn, LWup and LWdn) and explore the surface energy budget of a snow surface.

## How does it look ?

![Screenshot](https://github.com/ghislainp/snowseb/raw/master/screenshot1.png)


## Getting started

The easiest is using `pip`, the software is installed with:

```batch
pip install git+https://github.com/ghislainp/snowseb.git
```

and executed with:

```batch
./snowseb.py
```

Alternatively (not recommended), for a local installation, download and unzip (or git clone) the whole code, make the script `snowseb.py` executable and run it from the command line. On linux:

```batch
cd snowseb
chmod 755 snowseb.py
./snowseb.py
```


