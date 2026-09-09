#' Download spatial data of census tracts
#'
#' @description
#' Data of census tracts (setores censitários) of the Brazilian Population Census
#'
#' @template year
#' @param code_tract The 7-digit code of a municipality. Alternatively, if a
#'        two-digit state code or a two-letter uppercase abbreviation of a state
#'        is passed (e.g. `33` or `"RJ"`), all census tracts of that state are
#'        downloaded. Passing `code_tract = "all"` downloads all census tracts
#'        of the country. Municipality codes can be consulted with the
#'        `geobr::lookup_muni()` function. Unlike in most `geobr` functions,
#'        this argument is **required and has no default**: loading all census
#'        tracts of the country takes a long time and may exhaust memory, so the
#'        choice is left explicitly to the user.
#' @param zone For census tracts before 2010, 'urban' and 'rural' census tracts
#'             are separate data sets.
#' @template simplified
#' @template output
#' @template showProgress
#' @template cache
#' @template verbose
#'
#' @return An `"sf" "data.frame"` OR an `ArrowObject`
#'
#' @export
#'
#' @examplesIf identical(tolower(Sys.getenv("NOT_CRAN")), "true")
#'
#' # Read all census tracts of a state at a given year
#' c <- read_census_tract(year = 2022, code_tract = "DF")
#'
#' # Read all census tracts of a municipality at a given year
#' c <- read_census_tract(year = 2022, code_tract = 5201108)
#'
#' # Read all census tracts of the country at a given year
#' c <- read_census_tract(year = 2022, code_tract = "all")
#'
#' # Read rural census tracts for years before 2007
#' c <- read_census_tract(
#'   year = 2000,
#'   code_tract = 5201108,
#'   zone = "rural"
#'   )
#'
read_census_tract <- function(year,
                              code_tract,
                              zone = "urban",
                              simplified = TRUE,
                              output = "sf",
                              showProgress = TRUE,
                              cache = TRUE,
                              verbose = TRUE){

  # Get metadata with data url addresses
  temp_meta <- select_metadata(
    geography = c("censustracts", "censustractsrural", "censustractsurbano"),
    year = year,
    simplified = simplified
    )

  # check if download failed
  if (is.null(temp_meta)) { return(invisible(NULL)) }

  # Check zone input urban and rural inputs if year <=2007
  if (year <= 2007) {

    temp_meta <- temp_meta |>
      dplyr::filter(grepl(zone, file_name))

    if (nrow(temp_meta) == 0) {
      cli::cli_abort("Invalid Value to argument 'zone'. It must be either 'urban' or 'rural'")
    }

  }


  # check if download failed
  if (is.null(temp_meta)) { return(invisible(NULL)) }

  # download file and open arrow dataset
  temp_arrw <- download_parquet(
    filename_to_download = temp_meta$file_name,
    showProgress = showProgress,
    cache = cache
  )

  # check if download failed
  if (is.null(temp_arrw)) { return(invisible(NULL)) }

  # FILTER
  temp_arrw <- filter_arrw(temp_arrw, code = code_tract)

  # convert to sf
  temp <- convert_output(temp_arrw, output)

  return(temp)


  }
