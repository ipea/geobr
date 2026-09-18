#' geobr: Download Official Spatial Data Sets of Brazil
#'
#' Easy access to official spatial data sets of Brazil as 'sf' objects in R. The
#' package includes a wide range of geospatial data available at various
#' geographic scales and for various years with harmonized attributes,
#' projection and fixed topology.
#'
#' @section Usage:
#' Please check the vignettes for more on the package usage:
#' - Introduction to geobr (R) on the [website](
#' https://ipea.github.io/geobr/articles/intro_to_geobr.html).
#'
#' @docType package
#' @name geobr
#' @aliases geobr-package
#'
#' @importFrom utils "tail"
#' @importFrom methods is
#'
#' @keywords internal
"_PACKAGE"

## quiets concerns of R CMD check re: the .'s that appear in pipelines
if(getRversion() >= "2.15.1")  utils::globalVariables(c('brazil_2010', # nocov star
                                                        'grid_state_correspondence_table',
                                                        'data',
                                                        'geo',
                                                        'con',
                                                        'code',
                                                        'code_weighting_area',
                                                        'code_muni',
                                                        'code_state',
                                                        'code_abbrev',
                                                        'abbrev_state',
                                                        'code_region',
                                                        'name_region',
                                                        'name_muni_format',
                                                        'tp',
                                                        'filesD',
                                                        'temp_meta',
                                                        'group_by',
                                                        'showProgress',
                                                        'year',
                                                        'url2',
                                                        'file_name',
                                                        'name_muni_formatted',
                                                        'simplified',
                                                        'alias',
                                                        'date',
                                                        'temp_sf',
                                                        'code_pop_arrangement',
                                                        'code_urban_concentration',
                                                        'Function'
                                                        )) # nocov end

