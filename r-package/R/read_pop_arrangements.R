#' Download population arrangements in Brazil
#'
#' @description
#' This function reads the official data on the population arrangements (Arranjos
#' Populacionais) in Brazil. Original data by the Brazilian Institute of Geography
#' and Statistics (IBGE). More information about the methodology at \url{https://www.ibge.gov.br/geociencias/organizacao-do-territorio/divisao-regional/15782-arranjos-populacionais-e-concentracoes-urbanas-do-brasil.html}
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
#'
#' @examplesIf identical(tolower(Sys.getenv("NOT_CRAN")), "true")
#' # Read population arrangements in an specific year
#' pa <- read_pop_arrangements(year = 2010)
#'
read_pop_arrangements <- function(year,
                                  code_state = "all",
                                  simplified = TRUE,
                                  output = "sf",
                                  showProgress = TRUE,
                                  cache = TRUE,
                                  verbose = TRUE){

  # Get metadata with data url addresses
  temp_meta <- select_metadata(
    geography="poparrangements",
    year = year,
    simplified = simplified,
    verbose = verbose
  )

  # check if metadata download failed
  if (is.null(temp_meta)) { return(invisible(NULL)) } # nocov

  # download files
  temp_arrw <- download_parquet(
    filename_to_download = temp_meta$file_name,
    showProgress = showProgress,
    cache = cache
  )

  # check if download failed
  if (is.null(temp_arrw)) { return(invisible(NULL)) }

  # keep only pop_arrangement
  temp_arrw <- temp_arrw |>
    dplyr::filter(! is.na(code_pop_arrangement))

  # FILTER
  temp_arrw <- filter_arrw(temp_arrw, code = code_state)

  # convert to sf
  temp <- convert_output(temp_arrw, output)

  return(temp)
}
