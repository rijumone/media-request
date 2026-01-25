import os

# os.environ["URL"] = "https://jellyfin.example.com"
# os.environ["API_KEY"] = "MY_TOKEN"

import jellyfin
from jellyfin.generated.api_10_10.models.media_type import MediaType
from pprint import pprint

api = jellyfin.api(
    os.getenv("JELLYFIN_URL"), 
    os.getenv("JELLYFIN_API_KEY")
)

print(
    api.system.info.version,
    api.system.info.server_name
)

# for _ in api.items.search.recursive().all:
for _ in api.items.search.recursive().all:
    # import pdb;pdb.set_trace()
    if _.media_type == MediaType.VIDEO \
        and "Once Upon a Time... In ".lower() in _.name.lower()\
            and _.production_year == 2019:
        print('================================================')
        # pprint(_)
        print(_.name, _.media_type, _.type, _.production_year)
    # break