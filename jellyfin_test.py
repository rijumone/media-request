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

"""
Sample item:
BaseItemDto(name='The Matrix Reloaded', original_title=None, server_id='26d86cc4fb4041ccb3ae3fd63fe90dcc', id=UUID('6d550138-8b72-9370-d3c0-b88f8633e598'), etag=None, source_type=None, playlist_item_id=None, date_created=None, date_last_media_added=None, extra_type=None, airs_before_season_number=None, airs_after_season_number=None, airs_before_episode_number=None, can_delete=None, can_download=None, has_lyrics=None, has_subtitles=True, preferred_metadata_language=None, preferred_metadata_country_code=None, container='mov,mp4,m4a,3gp,3g2,mj2', sort_name=None, forced_sort_name=None, video3_d_format=None, premiere_date=datetime.datetime(2003, 5, 15, 0, 0, tzinfo=TzInfo(0)), external_urls=None, media_sources=None, critic_rating=74, production_locations=None, path=None, enable_media_source_display=None, official_rating='R', custom_rating=None, channel_id=None, channel_name=None, overview=None, taglines=None, genres=None, community_rating=7.068, cumulative_run_time_ticks=None, run_time_ticks=82955372500, play_access=None, aspect_ratio=None, production_year=2003, is_place_holder=None, number=None, channel_number=None, index_number=None, index_number_end=None, parent_index_number=None, remote_trailers=None, provider_ids=None, is_hd=None, is_folder=False, parent_id=None, type=<BaseItemKind.MOVIE: 'Movie'>, people=None, studios=None, genre_items=None, parent_logo_item_id=None, parent_backdrop_item_id=None, parent_backdrop_image_tags=None, local_trailer_count=None, user_data=UserItemDataDto(rating=None, played_percentage=None, unplayed_item_count=None, playback_position_ticks=0, play_count=0, is_favorite=False, likes=None, last_played_date=None, played=False, key='604', item_id=UUID('00000000-0000-0000-0000-000000000000')), recursive_item_count=None, child_count=None, series_name=None, series_id=None, season_id=None, special_feature_count=None, display_preferences_id=None, status=None, air_time=None, air_days=None, tags=None, primary_image_aspect_ratio=None, artists=None, artist_items=None, album=None, collection_type=None, display_order=None, album_id=None, album_primary_image_tag=None, series_primary_image_tag=None, album_artist=None, album_artists=None, season_name=None, media_streams=None, video_type=<VideoType.VIDEOFILE: 'VideoFile'>, part_count=None, media_source_count=None, image_tags={'Primary': 'b25235380ba41ab226831afead5bb0fc', 'Logo': '2fff2970de95e7c5ae84c2b22b9e4a61', 'Thumb': 'e06d7b2b43fea15a76951b0b5b85fea8'}, backdrop_image_tags=['1e780d913daeb68b309f164cd9e94b31'], screenshot_image_tags=None, parent_logo_image_tag=None, parent_art_item_id=None, parent_art_image_tag=None, series_thumb_image_tag=None, image_blur_hashes=BaseItemDtoImageBlurHashes(primary={'b25235380ba41ab226831afead5bb0fc': 'dF98I{?txVx[.QtQMyV[IVM|ICM|IBV[tQof8yRQx[of'}, art=None, backdrop={'1e780d913daeb68b309f164cd9e94b31': 'N01W4XyDDOH?xa.8H@RP%gx]MxMxoza0V@o}o}kC'}, banner=None, logo={'2fff2970de95e7c5ae84c2b22b9e4a61': 'HGBguIt74Tt7IANFRjMxoMMxWBMxWUxut7ofofxu'}, thumb={'e06d7b2b43fea15a76951b0b5b85fea8': 'N~Kn#akC%2%MV@WB~qoft7xuayay?bj[a{t7fkbG'}, disc=None, box=None, screenshot=None, menu=None, chapter=None, box_rear=None, profile=None), series_studio=None, parent_thumb_item_id=None, parent_thumb_image_tag=None, parent_primary_image_item_id=None, parent_primary_image_tag=None, chapters=None, trickplay=None, location_type=<LocationType.FILESYSTEM: 'FileSystem'>, iso_type=None, media_type=<MediaType.VIDEO: 'Video'>, end_date=None, locked_fields=None, trailer_count=None, movie_count=None, series_count=None, program_count=None, episode_count=None, song_count=None, album_count=None, artist_count=None, music_video_count=None, lock_data=None, width=None, height=None, camera_make=None, camera_model=None, software=None, exposure_time=None, focal_length=None, image_orientation=None, aperture=None, shutter_speed=None, latitude=None, longitude=None, altitude=None, iso_speed_rating=None, series_timer_id=None, program_id=None, channel_primary_image_tag=None, start_date=None, completion_percentage=None, is_repeat=None, episode_title=None, channel_type=None, audio=None, is_movie=None, is_sports=None, is_series=None, is_live=None, is_news=None, is_kids=None, is_premiere=None, timer_id=None, normalization_gain=None, current_program=None)
"""