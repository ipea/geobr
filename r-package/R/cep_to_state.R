#' Determine the state of a given CEP postal code
#'
#' @description
#' Zips codes in Brazil are known as CEP, the abbreviation for postal code
#' address. CEPs in Brazil are 8 digits long, with the format `'xxxxx-xxx'`.
#'
#' @param cep A character string with 8 digits in the format `"xxxxxxxx"`, or
#'            with the format `'xxxxx-xxx'`.
#' @return A character string with a state abbreviation.
#'
#' @export
#'
#' @examplesIf identical(tolower(Sys.getenv("NOT_CRAN")), "true")
#' uf <- cep_to_state(cep = '69900-000')
#'
#' # Or:
#' uf <- cep_to_state(cep = '69900000')
#'
cep_to_state <- function(cep){

  # reference
  # https://help.commerceplus.com.br/hc/pt-br/articles/115008224967-Faixas-de-CEP-por-Estado
  # https://mundoeducacao.bol.uol.com.br/curiosidades/o-que-significam-os-numeros-cep.htm

  # not null
  if (is.null(cep)) {stop("Error: 'cep' cannot be NULL.") }
  if (!is.character(cep)) {stop("Error: 'cep' must have class 'character'.") }

  # checks
  cep <- gsub("-", "", cep)
  if (!nchar(cep)==8) {stop("'cep' must have 8 digits.") }

  suppressWarnings({ cep <- as.numeric(cep) })
  if (is.na(cep)) {stop("'cep' input must have numerical digits.")}


  ceps <- list(
    list(state = "AC", range = c(69900000L, 69999999L)),
    list(state = "AL", range = c(57000000L, 57999999L)),
    list(state = "AM", range = c(69000000L, 69299999L)),
    list(state = "AM", range = c(69400000L, 69899999L)),
    list(state = "AP", range = c(68900000L, 68999999L)),
    list(state = "BA", range = c(40000000L, 48999999L)),
    list(state = "CE", range = c(60000000L, 63999999L)),
    list(state = "DF", range = c(70000000L, 72799999L)),
    list(state = "DF", range = c(73000000L, 73699999L)),
    list(state = "ES", range = c(29000000L,	29999999L)),
    list(state = "GO", range = c(72800000L, 72999999L)),
    list(state = "GO", range = c(73700000L, 76799999L)),
    list(state = "MA", range = c(65000000L, 65999999L)),
    list(state = "MG", range = c(30000000L, 39999999L)),
    list(state = "MS", range = c(79000000L, 79999999L)),
    list(state = "MT", range = c(78000000L, 78899999L)),
    list(state = "PA", range = c(66000000L, 68899999L)),
    list(state = "PB", range = c(58000000L, 58999999L)),
    list(state = "PE", range = c(50000000L, 56999999L)),
    list(state = "PI", range = c(64000000L, 64999999L)),
    list(state = "PR", range = c(80000000L, 87999999L)),
    list(state = "RJ", range = c(20000000L, 28999999L)),
    list(state = "RN", range = c(59000000L, 59999999L)),
    list(state = "RO", range = c(76800000L, 76999999L)),
    list(state = "RR", range = c(69300000L, 69399999L)),
    list(state = "RS", range = c(90000000L, 99999999L)),
    list(state = "SC", range = c(88000000L, 89999999L)),
    list(state = "SE", range = c(49000000L, 49999999L)),
    list(state = "SP", range = c(01000000L, 19999999L)),
    list(state = "TO", range = c(77000000L, 77999999L))
  )

  for (value in ceps) {
    if (cep >= value$range[1] && cep <= value$range[2]) {
      return(value$state)
    }
  }
  stop("CEP not found")
}
