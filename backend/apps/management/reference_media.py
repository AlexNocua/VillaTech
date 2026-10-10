"""Private reference delivery with byte ranges for video seeking."""
import re
from pathlib import Path
from django.http import FileResponse, HttpResponse, StreamingHttpResponse

TYPES={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp',
       '.mp4':'video/mp4','.mov':'video/quicktime','.webm':'video/webm'}


def reference_response(request, field, name):
    mime=TYPES.get(Path(field.name).suffix.lower())
    preview=request.GET.get('preview')=='1' and mime is not None
    stream=field.open('rb')
    size=field.size
    range_header=request.headers.get('Range') if preview else None
    if range_header:
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',range_header)
        valid=bool(match and any(match.groups()) and size)
        start,end=0,size-1
        if valid:
            first,last=match.groups()
            if first:
                start=int(first);end=min(int(last),size-1) if last else size-1
            else:
                count=int(last);valid=count>0;start=max(0,size-count)
            valid=valid and start<=end and start<size
        if not valid:
            stream.close();response=HttpResponse(status=416)
            response['Content-Range']=f'bytes */{size}'
        elif request.method=='HEAD':
            stream.close();response=HttpResponse(status=206,content_type=mime)
            response['Content-Range']=f'bytes {start}-{end}/{size}'
            response['Content-Length']=str(end-start+1)
        else:
            stream.seek(start)
            def chunks():
                remaining=end-start+1
                try:
                    while remaining:
                        chunk=stream.read(min(65536,remaining))
                        if not chunk:break
                        remaining-=len(chunk);yield chunk
                finally:stream.close()
            response=StreamingHttpResponse(chunks(),status=206,content_type=mime)
            response._resource_closers.append(stream.close)
            response['Content-Range']=f'bytes {start}-{end}/{size}'
            response['Content-Length']=str(end-start+1)
    elif request.method=='HEAD':
        stream.close();response=HttpResponse(content_type=mime if preview else 'application/octet-stream')
        response['Content-Length']=str(size)
    else:
        response=FileResponse(stream,as_attachment=not preview,filename=name,
            content_type=mime if preview else 'application/octet-stream')
    response['Cache-Control']='private, no-store'
    response['X-Content-Type-Options']='nosniff'
    response['Content-Security-Policy']="default-src 'none'; sandbox"
    if preview:response['Accept-Ranges']='bytes'
    return response
