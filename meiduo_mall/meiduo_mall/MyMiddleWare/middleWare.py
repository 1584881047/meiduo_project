def myMiddleWare(get_response):

    def innerMiddleWear(request):
        response = get_response(request)
        response['Access-Control-Allow-Origin'] = '*'

        return response

    return innerMiddleWear
