# pacotes pontos para chace ce arquivos
https://github.com/dfsp-spirit/pkgfilecache
https://gitlab.com/cnrgh/databases/r-fscache


#' Cache options
#' 1) criar gestao de etag in the house
#'
#' 2) {httr2} e remove arquivos .BODY
#'    - pode remover o body OU arquivo.
#'    - Soh nao pode apagar body & arquivo & manter rds
#'    - baixa de novo se arquivo atualiza: sim
#'
#' 3) usar {curl} multi_download (aguardando resposta sobre etag)
#'    - baixa de novo se arquivo atualiza: sim, SOH se tamanho de arquivo for diferente




ok # get etag of url
# create name of local_etag
# check if etag exsists locally / is identical
  # if yes, read local file
  # if now, save local tag and download file


# md5/hash of local file
tools::md5sum(files = '22municipality_2015.gpkg')


# long-term cache

library(sf)
library(httr)
library(httr2)
library(httpcache)
am <- 'https://github.com/ipea/censobr/releases/download/v0.3.0/1970_population_v0.3.0.parquet'
as <- 'https://github.com/ipea/geobr/releases/download/v1.7.0/amazonia_legal_simplified.gpkg'


url_d <- dput(file_url)


url <- c(
         "https://github.com/ipea/geobr/releases/download/v1.7.0/33municipality_2015.gpkg",
         # "https://github.com/ipea/geobr/releases/download/v1.7.0/35municipality_2015.gpkg",
         # "https://github.com/ipea/geobr/releases/download/v1.7.0/31municipality_2015.gpkg",
         # "https://github.com/ipea/geobr/releases/download/v1.7.0/11municipality_2015.gpkg",
         # "https://github.com/ipea/geobr/releases/download/v1.7.0/27municipality_2015.gpkg",
         # "https://github.com/ipea/geobr/releases/download/v1.7.0/26municipality_2015.gpkg",
         # "https://github.com/ipea/geobr/releases/download/v1.7.0/25municipality_2015.gpkg",
         # "https://github.com/ipea/geobr/releases/download/v1.7.0/24municipality_2015.gpkg",
         # "https://github.com/ipea/geobr/releases/download/v1.7.0/23municipality_2015.gpkg",
         # "https://github.com/ipea/geobr/releases/download/v1.7.0/22municipality_2015.gpkg",
         "https://github.com/ipea/geobr/releases/download/v1.7.0/21municipality_2015.gpkg"

)


#benchmark
library(tictoc)

tic()
downloaded_files <- curl::multi_download(
  urls = url,
  destfiles = basename(url),
  progress = TRUE,
  resume = T
)
toc()

# 5.38, 2.27

tic()
reqs <- lapply(X=url, FUN=httr2::request)
resp <- httr2::req_perform_parallel(req = reqs,
                                    progress = T,
                                    path = basename(url))

toc()
# 6.2, 4.69




















# otimo exemplo
# https://github.com/Robinlovelace/spanishoddata/blob/main/R/download_data.R
downloaded_files <- curl::multi_download(
  urls = url,
  destfiles = basename(url),
  progress = TRUE,
  resume = TRUE
)
return(downloaded_files$destfile)



# download file
download_files <- function(url){
  #input url
  #output path to local file

  dest_files <- basename(url)

    # Create a request object for the URL
    reqs <- lapply(X=url, FUN=httr2::request)


    # # Add SSL configuration to the request (disabling SSL verification)
    reqs <- lapply(X=reqs, FUN=httr2::req_options, ssl_verifypeer = FALSE)

    # download multiple files in parallel
    resp <- httr2::req_perform_parallel(req = reqs,
                                        progress = T,
                                        path = dest_files)

    return(dest_files)
  }


get_etag_code <- function(url){
  #input url
  #output etag code

  # function for single url
  get_single_etag <- function(url){

    # Step 1: Create a request object for the URL
    try(req <- httr2::request(url), silent = TRUE)

    # Step 2: Set the method to HEAD to only retrieve headers
    req <- httr2::req_method(req, "HEAD")

    # Step 3: Perform the request and capture the response
    try(resp <- httr2::req_perform(req), silent = TRUE)
    # if(is.null(req$body)){ message("No internet connection.") }

    # !!!!! check internet connection

    # Step 4: Extract the ETag from the response headers
    etag <- httr2::resp_header(resp, "etag")
    return(etag)
    }

  # results for input list
  out_etag <- lapply(X = url, FUN = get_single_etag)
  out_etag <- unlist(out_etag)
  return(out_etag)
}


# check if
check_if_downloaded <- function(url){

  etag_code <- get_etag_code(url)


}

create_local_etag <- function(url, file_extension = '.gpkg'){

  file_basename <- basename(url)
  etag_code <- get_etag_code(url)

  # create etag file name
  etag_filename <- paste0('etag_', file_basename)
  etag_filename <- gsub(file_extension, '.rds', etag_filename)

  # check etag one by one
  # check if etag already exists
  if (file.exists(etag_filename)) {

    # if etags are identical read return path to local file
    etag_local <- readRDS(etag_filename)
    if (identical(etag_local, )){
      return(file_basename)
    }

  }

  # if etag does not exist, save it
  saveRDS(etag_code, etag_filename)

}









# get all etags for metadata table
aaa <- lapply(X = c(am, as), FUN = function(x){HEAD(url = x)$headers$etag})
unlist(aaa)


f <- 'C:/Users/user/Downloads/amazonia_legal (2).gpkg'

file.info(f)$ctime

fff <- HEAD(url = f)



#' metadata table should have url and etag

#' DOWNLOAD fun
#' 1)if etag is not saved locally,
#' download fun should save etag locally and download data
#' if etag and data exists locally, then compare against metadata
#







library(tools)

dest_dir = gsub("////", "/", normalizePath(R_user_dir("ipeadata-db","cache"), mustWork = FALSE))
cache_dir = paste0(dest_dir,"/control")
if (isFALSE(dir.exists(cache_dir))) {
  dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
}

urls_ibge = c(
  "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2022/Brasil/BR/BR_Pais_2022.zip",
  "https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/alteracoes_toponimicas_municipais/Alteracoes_Toponimicas_Municipais_2022.xls",
  "https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/divisao_territorial/2022/DTB_2022.zip"
)

arqs_ibge = paste0(dest_dir,"/",basename(urls_ibge))




















#benchmark
library(tictoc)

url = 'https://github.com/ipea/censobr/releases/download/v0.3.1/test_2000_families.parquet'

tic()
downloaded_files <- curl::multi_download(
  urls = url,
  destfiles = basename(url),
  progress = TRUE,
  resume = T
)
toc()

# 10.2    1.7

tools::md5sum('test_2000_families.parquet') |> unname()

tools::md5sum(url) |> unname()



# cache with curl::multi_download ----------------------------------
library(tictoc)
url = 'https://github.com/ipea/censobr/releases/download/v0.3.1/test2_2000_families.parquet'

tictoc::tic()
downloaded_files <- curl::multi_download(
  urls = url,
  destfiles = basename(url),
  progress = TRUE,
  resume = T
)
tictoc::toc()
# first 3.7 sec elapsed

# second 1.01 sec elapsed 0.89 sec elapsed

# changed file


# cache with httr2 ----------------------------------

library(httr2)

url <- 'https://github.com/ipea/censobr/releases/download/v0.3.1/test2_2000_families.parquet'

reqs <- lapply(X=url, FUN=httr2::request)

reqs <- lapply(X=reqs, FUN=httr2::req_options,
               ssl_verifypeer = FALSE
               #  , nobody = TRUE
)

reqs2 <- lapply(X= reqs, FUN = httr2::req_cache, path = '.')

tictoc::tic()
resp <- httr2::req_perform_parallel(req = reqs2,
                                    progress = T,
                                    path = basename(url))
tictoc::toc()

# first 3.21 sec elapsed 0.99 sec elapsed


# second

# deleted body

# changed file

'9eb198b525e490ad929d1e4857eb4ec2.rds'

tools::md5sum(files = 'test2_2000_families.parquet')



system.time(

geobr::read_municipality(code_muni = 'all', year = 2010,cache = T)
)
