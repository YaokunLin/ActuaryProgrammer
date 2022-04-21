
PROJECT_ID=$(gcloud config list --format='value(core.project)')

textred=$(tput setaf 1) # Red
textgreen=$(tput setaf 2) # Green
textylw=$(tput setaf 3) # Yellow
textblue=$(tput setaf 4) # Blue
textpur=$(tput setaf 5) # Purple
textcyn=$(tput setaf 6) # Cyan
textwht=$(tput setaf 7) # White
textreset=$(tput sgr0) # Text reset.


which cloud_sql_proxy
if [[ $? != 0 ]]; then
    echo "${textred}Error: please add the location of your installed cloud_sql_proxy in your shell's profile/PATH"
    exit 1
fi

gcloud services enable sqladmin.googleapis.com
CLOUDSQL_CONNECTION_NAME=$(gcloud sql instances describe ${PROJECT_ID} --format "value(connectionName)")


cloud_sql_proxy -instances=${CLOUDSQL_CONNECTION_NAME}=tcp:5432