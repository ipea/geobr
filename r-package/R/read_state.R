#' Download spatial data of Brazilian states
#'
#' @description
#' Brazilian states
#'
#' @template year
#' @template code_state
#' @template simplified
#' @template output
#' @template showProgress
#' @template cache
#' @template verbose
#'
#' @return An `"sf" "data.frame"` OR an `ArrowObject`
#'
#' @export
#' @family area functions
#'
#' @examplesIf identical(tolower(Sys.getenv("NOT_CRAN")), "true")
#' # Read all states at a given year
#' ufs <- read_state(code_state="all", year = 2025)
#'
#' # Read specific state at a given year
#' uf <- read_state(code_state="SC", year = 2025)
#'
#' # Read specific state at a given year
#' uf <- read_state(code_state=12, year = 2025)
#'
read_state <- function(year,
                       code_state = "all",
                       simplified  = TRUE,
                       output = "sf",
                       showProgress = TRUE,
                       cache = TRUE,
                       verbose = TRUE){

  # Get metadata with data url addresses
  temp_meta <- select_metadata(
    geography="states",
    year = year,
    simplified = simplified,
    verbose = verbose
  )

  # check if metadata download failed
  if (is.null(temp_meta)) { return(invisible(NULL)) } # nocov

  # download files
  temp_arrw <- download_parquet(
    filename_to_download = temp_meta$file_name,
    showProgress,
    cache
    )

  # check if download failed
  if (is.null(temp_arrw)) { return(invisible(NULL)) } # nocov

  # FILTER
  temp_arrw <- filter_arrw(temp_arrw, code = code_state)

  # convert to sf
  temp <- convert_output(temp_arrw, output)

  return(temp)

  }
