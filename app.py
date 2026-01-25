import streamlit as st
import json
from pathlib import Path
import subprocess

# Page configuration
st.set_page_config(
    page_title="Riju's Movie Request Platform",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS for card styling
st.markdown("""
    <style>
    .movie-card {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    .movie-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.5);
    }
    .movie-title {
        font-size: 24px;
        font-weight: bold;
        color: #6cd4ff;
        margin-bottom: 10px;
    }
    .movie-year {
        color: #888;
        font-size: 16px;
    }
    .movie-rating {
        color: #ffd700;
        font-size: 18px;
        font-weight: bold;
    }
    .genre-tag {
        display: inline-block;
        background-color: #2d2d2d;
        color: #6cd4ff;
        padding: 5px 10px;
        margin: 5px 5px 5px 0;
        border-radius: 5px;
        font-size: 12px;
    }
    .quality-badge {
        display: inline-block;
        background-color: #4CAF50;
        color: white;
        padding: 3px 8px;
        margin: 2px;
        border-radius: 3px;
        font-size: 11px;
    }
    </style>
    """, unsafe_allow_html=True)

# Load JSON data
@st.cache_data
def load_data():
    with open('./out.json', 'r') as f:
        return json.load(f)

def select_best_magnet(magnet_links):
    """Select the best magnet link based on quality and type preferences."""
    if not magnet_links:
        return None
    
    # Quality preference order
    quality_order = ['1080p', '2160p', '720p', '480p', '3D']
    
    # Type preference patterns (in order)
    type_patterns = [
        lambda t: t.startswith('WEB'),  # WEB*
        lambda t: t == 'BluRay',        # BluRay
        lambda t: t.startswith('DVD'),  # DVD*
        lambda t: t.startswith('HD')    # HD*
    ]
    
    # Score each magnet link
    def score_link(link):
        quality = link.get('quality', '')
        link_type = link.get('type', '')
        
        # Quality score (lower is better)
        try:
            quality_score = quality_order.index(quality)
        except ValueError:
            quality_score = len(quality_order)  # Unknown quality gets lowest priority
        
        # Type score (lower is better)
        type_score = len(type_patterns)  # Default to lowest priority
        for idx, pattern in enumerate(type_patterns):
            if pattern(link_type):
                type_score = idx
                break
        
        # Return tuple for sorting (quality first, then type)
        return (quality_score, type_score)
    
    # Sort and return the best link
    best_link = min(magnet_links, key=score_link)
    return best_link

def request_movie(magnet_url, movie_title):
    """Run subprocess command to request a movie."""
    try:
        # Using echo as placeholder - replace with actual command later
        result = subprocess.run(
            ['echo', magnet_url],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(result.stdout)
        if result.returncode == 0:
            st.success(f"✅ Request submitted for: {movie_title}")
            st.code(result.stdout, language=None)
        else:
            st.error(f"❌ Request failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        st.error("⏱️ Request timed out")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

data = load_data()

# Header
st.title("🎬 Riju's Movie Request Platform")
st.markdown(f"**Total Movies:** {len(data['media'])}")

# Sidebar filters
st.sidebar.header("Filters")

# Search
search_query = st.sidebar.text_input("🔍 Search by title", "")
search_cast = st.sidebar.text_input("🎭 Search by cast", "")
search_director = st.sidebar.text_input("🎬 Search by director", "")

# Year filter
years = sorted(set(movie['year'] for movie in data['media']), reverse=True)
selected_years = st.sidebar.multiselect("Year", years)

# Genre filter
all_genres = sorted(set(genre for movie in data['media'] for genre in movie.get('genres', [])))
selected_genres = st.sidebar.multiselect("Genre", all_genres)

# Quality filter
selected_qualities = st.sidebar.multiselect("Quality", data['supported_qualities'])

# Rating filter
min_rating = st.sidebar.slider("Minimum IMDB Rating", 0.0, 10.0, 0.0, 0.1)

# Sort options
sort_option = st.sidebar.selectbox("Sort by", ["Year (Newest)", "Year (Oldest)", "Title", "Rating (Highest)", "Rating (Lowest)"])

# Pagination settings
st.sidebar.divider()
st.sidebar.header("Pagination")
items_per_page = st.sidebar.selectbox("Items per page", [6, 9, 12, 18, 24, 30], index=1)

# Filter movies
filtered_movies = data['media']

if search_query:
    filtered_movies = [m for m in filtered_movies if search_query.lower() in m['title'].lower()]

if search_cast:
    filtered_movies = [m for m in filtered_movies if any(
        search_cast.lower() in cast_member.lower() for cast_member in m.get('cast', [])
    )]

if search_director:
    filtered_movies = [m for m in filtered_movies if search_director.lower() in m.get('director', '').lower()]

if selected_years:
    filtered_movies = [m for m in filtered_movies if m['year'] in selected_years]

if selected_genres:
    filtered_movies = [m for m in filtered_movies if any(g in m.get('genres', []) for g in selected_genres)]

if selected_qualities:
    filtered_movies = [m for m in filtered_movies if any(
        link['quality'] in selected_qualities for link in m.get('magnet_links', [])
    )]

filtered_movies = [m for m in filtered_movies if m.get('imdb_rating', 0) >= min_rating]

# Sort movies
if sort_option == "Title":
    filtered_movies.sort(key=lambda x: x['title'])
elif sort_option == "Year (Newest)":
    filtered_movies.sort(key=lambda x: x['year'], reverse=True)
elif sort_option == "Year (Oldest)":
    filtered_movies.sort(key=lambda x: x['year'])
elif sort_option == "Rating (Highest)":
    filtered_movies.sort(key=lambda x: x.get('imdb_rating', 0), reverse=True)
elif sort_option == "Rating (Lowest)":
    filtered_movies.sort(key=lambda x: x.get('imdb_rating', 0))

# Pagination logic
total_movies = len(filtered_movies)
total_pages = (total_movies + items_per_page - 1) // items_per_page

# Initialize page number in session state if not exists
if 'page_number' not in st.session_state:
    st.session_state.page_number = 1

# Ensure page number is within bounds when filters change
if st.session_state.page_number > total_pages and total_pages > 0:
    st.session_state.page_number = total_pages
elif st.session_state.page_number < 1:
    st.session_state.page_number = 1

if total_pages > 0:
    current_page = st.session_state.page_number
    
    # Top page navigation
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⏮️ First", width='stretch', disabled=(current_page == 1), key="top_first_btn"):
            st.session_state.page_number = 1
            st.rerun()
    
    with col2:
        if st.button("⬅️ Prev", width='stretch', disabled=(current_page == 1), key="top_prev_btn"):
            st.session_state.page_number = current_page - 1
            st.rerun()
    
    with col3:
        st.markdown(f"<div style='text-align: center; padding-top: 8px;'><strong>Page {current_page} of {total_pages}</strong></div>", unsafe_allow_html=True)
    
    with col4:
        if st.button("Next ➡️", width='stretch', disabled=(current_page == total_pages), key="top_next_btn"):
            st.session_state.page_number = current_page + 1
            st.rerun()
    
    with col5:
        if st.button("Last ⏭️", width='stretch', disabled=(current_page == total_pages), key="top_last_btn"):
            st.session_state.page_number = total_pages
            st.rerun()
    
    # Calculate start and end indices
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_movies)
    
    # Slice the filtered movies for current page
    filtered_movies = filtered_movies[start_idx:end_idx]
    
    st.markdown(f"**Showing {start_idx + 1}-{end_idx} of {total_movies} movies**")
else:
    st.markdown("**No movies found**")

# Display movies in grid
cols_per_row = 3
for i in range(0, len(filtered_movies), cols_per_row):
    cols = st.columns(cols_per_row)
    for idx, col in enumerate(cols):
        if i + idx < len(filtered_movies):
            movie = filtered_movies[i + idx]
            with col:
                # Movie poster
                if movie.get('poster') and movie['poster'].get('url'):
                    st.image(movie['poster']['url'], width='stretch')
                
                # Movie title and year
                st.markdown(f"### {movie['title']} ({movie['year']})")
                
                # IMDB Rating
                if movie.get('imdb_rating'):
                    st.markdown(f"⭐ **{movie['imdb_rating']}/10** IMDB")
                
                # Genres
                if movie.get('genres'):
                    genres_html = " ".join([f'<span class="genre-tag">{g}</span>' for g in movie['genres']])
                    st.markdown(genres_html, unsafe_allow_html=True)
                
                # Synopsis
                if movie.get('synopsis'):
                    with st.expander("📖 Synopsis"):
                        st.write(movie['synopsis'])
                
                # Director and Cast
                if movie.get('director'):
                    st.markdown(f"**Director:** {movie['director']}")
                
                if movie.get('cast'):
                    with st.expander("🎭 Cast"):
                        st.write(", ".join(movie['cast']))
                
                # Available qualities
                if movie.get('magnet_links'):
                    qualities = set(f"{link['quality']} {link['type']}" for link in movie['magnet_links'])
                    quality_badges = " ".join([f'<span class="quality-badge">{q}</span>' for q in sorted(qualities)])
                    st.markdown("**Available:**", unsafe_allow_html=True)
                    st.markdown(quality_badges, unsafe_allow_html=True)
                
                # Links
                col1, col2, col3 = st.columns(3)
                with col1:
                    if movie.get('imdb_link'):
                        st.link_button("IMDB", movie['imdb_link'], width='stretch')
                
                with col2:
                    if movie.get('magnet_links'):
                        with st.popover("🧲 Magnets"):
                            for link in movie['magnet_links']:
                                st.markdown(f"**{link['quality']} {link['type']}**")
                                st.code(link['url'], language=None)
                
                with col3:
                    if movie.get('magnet_links'):
                        best_magnet = select_best_magnet(movie['magnet_links'])
                        if best_magnet and st.button("📥 Request", width='stretch', key=f"request_{movie['slug']}"):
                            request_movie(best_magnet['url'], movie['title'])
                
                st.divider()

# Page navigation at bottom
if total_pages > 1:
    st.divider()
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    current_page = st.session_state.page_number
    
    with col1:
        if st.button("⏮️ First", width='stretch', disabled=(current_page == 1), key="first_btn"):
            st.session_state.page_number = 1
            st.rerun()
    
    with col2:
        if st.button("⬅️ Previous", width='stretch', disabled=(current_page == 1), key="prev_btn"):
            st.session_state.page_number = current_page - 1
            st.rerun()
    
    with col3:
        st.markdown(f"<div style='text-align: center; padding-top: 8px;'><strong>Page {current_page} of {total_pages}</strong></div>", unsafe_allow_html=True)
    
    with col4:
        if st.button("Next ➡️", width='stretch', disabled=(current_page == total_pages), key="next_btn"):
            st.session_state.page_number = current_page + 1
            st.rerun()
    
    with col5:
        if st.button("Last ⏭️", width='stretch', disabled=(current_page == total_pages), key="last_btn"):
            st.session_state.page_number = total_pages
            st.rerun()
