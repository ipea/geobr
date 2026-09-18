#' Download geolocated data of addresses in Brazil
#'
#' @description
#' This function reads the data of the National Registry of Addresses for
#' Statistical Purposes (Cadastro Nacional de Enderecos para Fins Estatisticos,
#' CNEFE), organized by the Brazilian Institute of Geography and Statistics
#' (IBGE). The data brings the geographical coordinates (lat lon) of every
#' address surveyed in the Population Census, along with the census tract and
#' municipality each address belongs to, its postal code (CEP), the type of
#' building (`cod_especie`) and the precision level of its coordinates
#' (`nv_geo_coord`). More information available at
#' \url{https://www.ibge.gov.br/estatisticas/sociais/populacao/38734-cadastro-nacional-de-enderecos-para-fins-estatisticos.html}.
#'
#' Note this is a very large data set: the 2022 CNEFE covers roughly 111 million
#' addresses in a single 1.2 GB file. The file is downloaded in full and only
#' then filtered by `code_muni`, so the first call in an R session takes a long
#' time even when a single municipality is requested. Subsequent calls reuse the
#' cached file. Passing `output = "duckdb"` avoids loading the result into memory.
#'
#' @template year
#' @param code_muni The 7-digit code of a municipality. Alternatively, if a
#'        two-digit state code or a two-letter uppercase abbreviation of a state
#'        is passed (e.g. `33` or `"RJ"`), all data of that state are
#'        downloaded. Passing `code_muni = "all"` downloads the addresses of the
#'        whole country. Municipality codes can be consulted with the
#'        `geobr::lookup_muni()` function. Unlike in most `geobr` functions,
#'        this argument is **required and has no default**: reading the
#'        addresses of the whole country may exhaust memory, so the choice is
#'        left explicitly to the user.
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
#' # Read all addresses in a given municipality
#' add <- read_addresses(
#'   year = 2022,
#'   code_muni = 3304557
#'   )
#'
#' # Read all addresses in a given state, without loading them into memory
#' add_rj <- read_addresses(
#'   year = 2022,
#'   code_muni = "RJ",
#'   output = "duckdb"
#'   )
#'
read_addresses <- function(year,
                           code_muni,
                           output = "sf",
                           showProgress = TRUE,
                           cache = TRUE,
                           verbose = TRUE){

  # `code_muni` is required. Checked up front, before the download, so the user
  # is not made to wait for a 1.2 GB file only to hit a missing-argument error.
  if (missing(code_muni)) {
    cli::cli_abort(c(
      "Argument {.arg code_muni} is required and has no default.",
      "i" = "Pass a 7-digit municipality code, a state code or abbreviation (e.g. {.val RJ}), or {.val all} to read the whole country."
    ))
  }

  # Get metadata with data url addresses
  temp_meta <- select_metadata(
    geography="cnefe",
    year = year,
    simplified = FALSE,
    verbose = verbose
  )

  # check if metadata download failed
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
  temp_arrw <- filter_arrw(temp_arrw, code = code_muni)

  # convert to sf
  temp <- convert_output(temp_arrw, output)

  return(temp)

}
