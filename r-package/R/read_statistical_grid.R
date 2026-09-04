#' Download spatial data of IBGE's statistical grid
#'
#' @description
#' Official gridded population estimate of Brazil.
#'
#' @template year
#' @param code_muni The 7-digit code of a municipality. Alternatively, if a
#'        two-digit state code or a two-letter uppercase abbreviation of a state
#'        is passed (e.g. `33` or `"RJ"`), all data of that state are
#'        downloaded. Passing `code_muni = "all"` downloads the grid for the
#'        whole country. Municipality codes can be consulted with the
#'        `geobr::lookup_muni()` function. Unlike in most `geobr` functions,
#'        this argument is **required and has no default**: loading the grid for
#'        the whole country takes a long time and may exhaust memory, so the
#'        choice is left explicitly to the user.
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
#' # Read the grid covering a given state at a given year
#' grid_rio <- read_statistical_grid(
#'   year = 2022,
#'   code_muni = "RJ"
#'   )
#'
#' # Read the grid covering a given municipality at a given year
#' grid_ssalvador <- read_statistical_grid(
#'   year = 2022,
#'   code_muni = 2927408
#'   )
#'
read_statistical_grid <- function(year,
                                  code_muni,
                                  output = "sf",
                                  showProgress = TRUE,
                                  cache = TRUE,
                                  verbose = TRUE){

  # Get metadata with data url addresses
  temp_meta <- select_metadata(
    geography="statsgrid",
    year = year,
    simplified = FALSE,
    verbose = verbose
  )

  # check if metadata download failed
  if (is.null(temp_meta)) { return(invisible(NULL)) }

  # download files
  temp_arrw <- download_parquet(
    filename_to_download = temp_meta$file_name,
    showProgress,
    cache
  )

  # check if download failed
  if (is.null(temp_arrw)) { return(invisible(NULL)) }

  # FILTER
  temp_arrw <- filter_arrw(temp_arrw, code = code_muni)

  # convert to sf
  temp <- convert_output(temp_arrw, output)

  return(temp)

  }
