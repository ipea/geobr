#' List all data sets available in the geobr package
#'
#' @description
#' Returns a data frame with all data sets available in the geobr package
#'
#' @param wide Whether the the output data frame should come in wide (`TRUE`) or
#'        long format (`FALSE`).
#'
#' @return A `data.frame`
#'
#' @export
#'
#' @examplesIf identical(tolower(Sys.getenv("NOT_CRAN")), "true")
#' df <- list_geobr()
#'
list_geobr <- function(wide = TRUE){

  checkmate::assert_logical(wide, len = 1, any.missing = FALSE)

  # download metadata
  metadata <- download_metadata2()

  # check if metadata download failed
  if (is.null(metadata)) { return(invisible(NULL)) } # nocov

  # select cols
  tempdf <- metadata |>
    dplyr::select(alias = geo, year) |>
    dplyr::mutate(
      alias = ifelse(alias %in% c('censustractsurbano', 'censustractsrural'), 'censustracts', alias)) |>
    unique()


  # reformat to wide
  if (isTRUE(wide)) {
    tempdf <- tempdf |>
      dplyr::group_by(alias) |>
      dplyr::summarise( year = paste0(year, collapse = ', '))
  }

  datasets <- data.frame(
  Function = c(
    "read_country",
    "read_region",
    "read_state",
    "read_meso_region",
    "read_micro_region",
    "read_intermediate_region",
    "read_immediate_region",
    "read_municipality",
    "read_municipal_seat",
    "read_weighting_area",
    "read_census_tract",
    "read_statistical_grid",
    "read_metro_area",
    "read_urban_area",
    "read_amazon",
    "read_biomes",
    "read_conservation_units",
    "read_disaster_risk_area",
    "read_indigenous_land",
    "read_semiarid",
    "read_health_facilities",
    "read_health_region",
    "read_neighborhood",
    "read_schools",
    "read_comparable_areas",
    "read_urban_concentrations",
    "read_pop_arrangements",
    "read_favela",
    "read_polling_places",
    "read_quilombola_land",
    "read_capitals"
    ),
 geography = c(
   "Country",
   "Region",
   "States",
   "Meso region",
   "Micro region",
   "Intermediate region",
   "Immediate region",
   "Municipality",
   "Municipality seats (sedes municipais)",
   "Census weighting area (\u00e1rea de pondera\u00e7\u00e3o)",
   "Census tract (setor censit\u00e1rio)",
   "Statistical Grid (gridded population)",
   "Metropolitan areas",
   "Urban footprints",
   "Brazil's Legal Amazon",
   "Biomes",
   "Environmental Conservation Units",
   "Disaster risk areas",
   "Indigenous lands",
   "Semi Arid region",
   "Health facilities",
   "Health regions and macro regions",
   "Neighborhood limits",
   "Schools",
   "Historically comparable municipalities, aka \u00e1reas m\u00ednimas compar\u00e1veis (AMCs)",
   "Urban concentration areas (concentra\u00e7\u00f5es urbanas)",
   "Population arrangements (arranjos populacionais)",
   "Favelas and urban communities",
   "Voting places",
   "Quilombola lands officialy recognized",
   "State capitals"
 ),
 source = c(
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "MMA",
   "IBGE",
   "MMA",
   "CEMADEN and IBGE",
   "FUNAI",
   "IBGE",
   "CNES, DataSUS",
   "DataSUS",
   "IBGE",
   "INEP",
   "IBGE",
   "IBGE",
   "IBGE",
   "IBGE",
   "TSE",
   "Incra",
   "IBGE"
   ),

 alias = c(
   "country",
   "regions",
   "states",
   "mesoregions",
   "microregions",
   "intermediateregions",
   "immediateregions",
   "municipalities",
   "municipalseats",
   "weightingareas",
   "censustracts",
   "statsgrid",
   "metroarea",
   "urbanareas",
   "amazonialegal",
   "biomes",
   "conservationunits",
   "disasterriskareas",
   "indigenouslands",
   "semiarid",
   "healthfacilities",
   "healthregions",
   "neighborhoods",
   "schools",
   "comparableareas",
   "poparrangements",
   "poparrangements",
   "favelas",
   "pollingplaces",
   "quilombolalands",
   "capitals"
 ),
 stringsAsFactors = FALSE
 )

  df <- dplyr::left_join(
    x = datasets,
    y = tempdf,
    by  = 'alias',
    relationship = "many-to-many"
    ) |>
    dplyr::arrange(alias) |>
    dplyr::select(-alias)

  # data sets whose year is not given by the metadata
  df <- df |>
    dplyr::mutate(
      # AMCs temporarily suspended
      year = ifelse(Function == "read_comparable_areas", "temporarily suspended", year),
      # read_capitals() takes no year: it is built from the 2010 municipal seats
      year = ifelse(Function == "read_capitals", "2010", year)
    )

  return(df)
}
