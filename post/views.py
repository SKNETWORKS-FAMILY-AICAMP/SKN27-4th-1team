from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from .models import Post

# Pre-defined initial dummy data if DB is empty to keep aesthetic flow
INITIAL_POSTS = [
    {
        'category': 'WITNESS',
        'title': '새벽마다 같은 계단을 내려오는 발소리',
        'region': '서울 마포구',
        'body': '옥상 문이 잠긴 뒤에도 위층에서 누군가 내려오는 소리가 납니다. 발소리는 4층에서 멈추고, 그때 복도 센서등이 꺼집니다. 관리실 CCTV에는 아무도 찍히지 않았지만, 계단 난간에는 젖은 손자국이 남아 있었습니다.',
        'views': 182,
        'likes': 0
    },
    {
        'category': 'WITNESS',
        'title': '공중전화 부스 안쪽의 젖은 손자국',
        'region': '대구 중구',
        'body': '철거된 줄 알았던 공중전화가 비 오는 날만 골목에 나타납니다. 수화기를 들면 자기 목소리로 집 주소를 말합니다. 전화를 끊으면 부스 유리에 안쪽에서 찍힌 듯한 젖은 손자국이 생깁니다.',
        'views': 97,
        'likes': 0
    },
    {
        'category': 'WITNESS',
        'title': '터널 중간에서 라디오가 잡은 이름',
        'region': '강원 인제',
        'body': '터널 안에서는 모든 주파수가 끊기는데, 03:12에만 낯선 안내 방송이 나옵니다. 마지막에 제 이름을 불렀습니다. 다음 날 차량 블랙박스에는 터널 중간에 서 있던 사람이 조수석을 바라보는 장면이 남아 있었습니다.',
        'views': 211,
        'likes': 0
    },
    {
        'category': 'WITNESS',
        'title': '사진마다 한 칸씩 가까워지는 사람',
        'region': '전북 군산',
        'body': "폐가를 찍은 사진을 넘길수록 창문 안쪽의 사람이 한 칸씩 앞으로 옵니다. 마지막 사진은 아직 열어보지 않았습니다. 파일 이름은 자동으로 '다음은 네 방'으로 바뀌어 있었습니다.",
        'views': 144,
        'likes': 0
    },
    {
        'category': 'WITNESS',
        'title': '엘리베이터에 없는 지하 4층',
        'region': '경기 수원',
        'body': "버튼에는 없는데 표시창에만 B4가 뜹니다. 문이 열리면 항상 같은 안내문이 붙어 있습니다. '돌아가지 마시오.' 닫힘 버튼을 누른 뒤에도 문틈으로 같은 안내문이 점점 가까워졌습니다.",
        'views': 128,
        'likes': 0
    },
    {
        'category': 'CREATION',
        'title': '새벽 세 시에만 열리는 검색창',
        'region': '도시전설',
        'body': '검색어를 입력하면 결과가 아니라 사용자의 내일 일정이 뜹니다. 가장 아래에는 항상 삭제할 수 없는 방문 기록이 남습니다. 방문 기록의 마지막 주소는 아직 만들어지지 않은 사용자의 무덤 페이지입니다.',
        'views': 0,
        'likes': 31
    },
    {
        'category': 'CREATION',
        'title': '프로필 사진을 바꾸지 마세요',
        'region': '도플갱어',
        'body': '사진 속 얼굴이 하루에 한 번씩 표정을 바꿉니다. 일주일 뒤에는 사진 속 사람이 먼저 로그인합니다. 비밀번호는 사용자가 평생 쓰지 않았지만 잊은 적 없는 단어였습니다.',
        'views': 0,
        'likes': 18
    },
    {
        'category': 'CREATION',
        'title': '읽은 사람만 보이는 각주',
        'region': '저주',
        'body': '괴담 끝의 각주는 독자마다 다르게 보입니다. 자신의 이름이 적힌 각주를 읽은 사람은 다음 이야기에 등장합니다. 각주를 지우려면 아직 쓰이지 않은 결말을 먼저 읽어야 합니다.',
        'views': 0,
        'likes': 26
    }
]

@ensure_csrf_cookie
def mokgyeokgirok_view(request):
    """Renders the witness board page."""
    # Seed initial dummy data if database is empty
    if not Post.objects.exists():
        for dummy in INITIAL_POSTS:
            Post.objects.create(
                category=dummy['category'],
                title=dummy['title'],
                region=dummy['region'],
                body=dummy['body'],
                views=dummy['views'],
                likes=dummy['likes']
            )

    witness_posts = Post.objects.filter(category='WITNESS')
    creation_posts = Post.objects.filter(category='CREATION')

    context = {
        'witness_posts': witness_posts,
        'creation_posts': creation_posts,
    }
    return render(request, 'post/mokgyeokgirok.html', context)

def post_create_api(request):
    """API endpoint to create a post."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)
    
    try:
        data = json.loads(request.body)
        category_str = data.get('category', 'WITNESS').upper()
        # Convert front-end board id to Model choice
        category = 'CREATION' if 'CREATION' in category_str or 'CREATIONBOARD' in category_str else 'WITNESS'
        
        post = Post.objects.create(
            category=category,
            title=data.get('title', '제목 없는 기록').strip(),
            region=data.get('region', '지역 미상').strip(),
            body=data.get('body', '').strip(),
            views=0,
            likes=0
        )
        
        number_str = f"#C{str(post.id).zfill(3)}" if post.category == 'CREATION' else f"#{str(post.id).zfill(4)}"

        return JsonResponse({
            'status': 'success',
            'post': {
                'id': post.id,
                'category': post.category,
                'title': post.title,
                'region': post.region,
                'body': post.body,
                'number_str': number_str,
                'views': post.views,
                'likes': post.likes
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def post_detail_api(request, post_id):
    """API endpoint to fetch details of a post and increment view count."""
    post = get_object_or_404(Post, id=post_id)
    if post.category == 'WITNESS':
        post.views += 1
        post.save(update_fields=['views'])

    number_str = f"#C{str(post.id).zfill(3)}" if post.category == 'CREATION' else f"#{str(post.id).zfill(4)}"

    return JsonResponse({
        'status': 'success',
        'post': {
            'id': post.id,
            'category': post.category,
            'title': post.title,
            'region': post.region,
            'body': post.body,
            'number_str': number_str,
            'views': post.views,
            'likes': post.likes
        }
    })

def post_like_api(request, post_id):
    """API endpoint to increment recommendation (like) count for creation posts."""
    post = get_object_or_404(Post, id=post_id)
    post.likes += 1
    post.save(update_fields=['likes'])

    return JsonResponse({
        'status': 'success',
        'likes': post.likes
    })

