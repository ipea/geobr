#' Download spatial data of Brazilian health regions and health macro regions
#'
#' @description
#' Health regions are used to guide the the regional and state planning of health
#' services. Macro health regions, in particular, are used to guide the planning
#' of high complexity #' health services. These services involve larger economics
#' of scale and are concentrated in few municipalities because they are generally
#' more technology intensive, costly and face shortages of specialized
#' professionals. A macro region comprises one or more health regions.
#'
#' @template year
#' @template code_state
#' @param geometry_level String. Spatial level of the output geometries. Use
#'        `"municipality"` to return municipal geometries (default), `"micro"`
#'        to aggregate geometries by health region, or `"macro"` to aggregate
#'        geometries by health macroregion.
#' @param macro The argument `macro` has been deprecated.
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
#' # Read municipalities with info on health regions
#' health_muni <- read_health_region(year = 2024)
#'
#' # Read the geometries of micro regions
#' health_micro <- read_health_region(
#'   year = 2024,
#'   geometry_level = "micro"
#'   )
#'
#' # Read the geometries of macro regions
#' health_macro <- read_health_region(
#'   year = 2024,
#'   geometry_level = "macro"
#' )
#'
read_health_region <- function(year,
                               code_state = "all",
                               geometry_level = "municipality",
                               macro = NULL,
                               simplified = TRUE,
                               output = "sf",
                               showProgress = TRUE,
                               cache = TRUE,
                               verbose = TRUE){


  if (!is.null(macro)) {
    cli::cli_abort(c(
      "Argument deprecated",
      "x" = "The `macro` argument is deprecated. Use `geometry_level` instead."
    ))
  }


  # check input
  allowed <- c("municipality", "micro", "macro")
  if (!all(geometry_level %in% allowed)) {
    cli::cli_abort(c(
      "`geometry_level` must be one of: {.val {allowed}}.",
      "x" = "Invalid value{?s}: {.val {setdiff(geometry_level, allowed)}}."
    ))
  }

  # Get metadata
  temp_meta <- select_metadata(
    geography = "healthregions",
    year = year,
    simplified = simplified,
    verbose = verbose
  )

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
  temp_arrw <- filter_arrw(temp_arrw, code = code_state)

  # geometry_level
  if (geometry_level=="municipality") {

    # convert to sf
    temp <- convert_output(temp_arrw, output)

    return(temp)
  }

  # if micro or macro, perform aggregation
    # convert to sf
    temp <- convert_output(temp_arrw, "sf")

    all_cols <- names(temp)

    # Columns dropped before aggregating, matched by prefix so that
    # municipality-level variants such as `code_muni6` (present in the
    # 1991-2013 files) are dropped as well. Keeping `code_muni6` in the
    # grouping would silently defeat the aggregation. Mirrors the Python side.
    if(geometry_level=="micro"){
      drop_pattern <- '^(geometry|code_muni|name_muni|code_health_macroregion|name_health_macroregion)'
    } else {
      drop_pattern <- '^(geometry|code_muni|name_muni|code_health_region|name_health_region)'
    }

    group_cols <- all_cols[!grepl(drop_pattern, all_cols)]

    temp <- duckspatial::ddbs_union_agg(
      x = temp,
      by = group_cols
      ) |>
      duckspatial::ddbs_collect() |>
      sfheaders::sf_remove_holes()

  # convert to sf
    temp <- convert_output(temp, output)

  return(temp)

}
