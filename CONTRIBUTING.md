

# Become a contributor to **geobr** <img align="right" src="r-package/man/figures/geobr_logo_b.png" alt="logo" width="170"> <img align="right" src="r-package/man/figures/geobr_logo_y.png" alt="logo" width="170">

If you would like to contribute to **geobr**, the first thing to do is to open a [Github issue](https://github.com/ipea/geobr/issues) with your suggestion of ***function*** or ***dataset*** you would like to see in the package. Keep in mind that, as a rule, the package only includes geospatial data sets with national spatial coverage that are created/managed by govermental institutions and which are publicly available. 

The inclusion of every dataset in geobr follows a three-step process, as follows:

### Step 1. Data preparation
In the first step, the contributor should write an `R` script that will prepare the raw original data set to be used in geobr. This script should (1) download the raw data from the original website source, (2) rename column names following a simple spelling convention*, (3) ensure the data uses spatial projection EPSG 4674, (4) ensure every string column is `as.character` with UTF-8 encoding, (5) fix eventual topology issues in the data, and (6) save the data in `.rds` format.

This script can use any `R` package, but it needs to be 100% reproducible. There is a simple model [here](https://github.com/ipea/geobr/blob/master/r-package/prep_data/prep_example.R) and various preparation scripts in the [prep_data directory](https://github.com/ipea/geobr/blob/master/r-package/prep_data) that you can use as a reference. Mind you though that every data set has its own particularities so every prep_ script will be a little bit different accordingly.


### Step 2. Data validation and upload

Once the prep_ script is ready, the geobr team will test the script and validate the data output. If everything works fine, the geobr team will upload the data to our servers so it will become available for download.


### Step 3. Download and test functions

The 3rd step is perhaps the simplest one. In this step the contributor should write the package function that will be used to download the data. Most dowload functions have relatively simple structure and documentation. Please, have a look at some of the [other geobr functions](https://github.com/ipea/geobr/tree/master/r-package/R) for a reference. Function names should also follow our simple spelling convention*.

Once the download script is ready, the geobr team will write a script to test the function ([examples here](https://github.com/ipea/geobr/tree/master/r-package/tests/testthat)). If everything works fine, the contributor can open a [pull request](http://r-pkgs.had.co.nz/git.html#pr-make) and start the celebration. We will update our documentation to add your name to our contributors team.


**Spelling conventions**: Names should be lower case, short, use underscore when necessary, use English American spelling. Please have a look at the columns names and functions used in in geobr, and don't hesitate to contact if you have any question.


-----

Please note that the ‘geobr’ project is released with a [Contributor Code of Conduct](https://github.com/ipea/geobr/blob/master/CONDUCT.md). By contributing to this project, you agree to abide by its terms.
