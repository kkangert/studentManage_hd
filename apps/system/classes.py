from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import professionManage, classesManage, classesBindProfession, studentManage
from utils.tools import getIndex, listSplit


def addClasses(requestData):
    """
    创建班级操作函数
    :param requestData:
    :return:
    """
    professionCode = requestData['bindProfession'][0]
    classesName = requestData['classesName']

    if classesManage.objects.filter(classesName=classesName).values():
        return JsonResponse({'ret': 1, 'data': '已有相同名称班级,请重命名！'})
    else:
        index = getIndex(classesManage, 'classesCode')
        if classesManage.objects.create(classesCode=index, classesName=classesName,
                                        classesLevel=requestData['classesLevel']):
            classesCode = list(classesManage.objects.filter(classesName=classesName).values())[0]['classesCode']
            if classesBindProfession.objects.filter(classesCode=classesCode).count() > 0:
                return JsonResponse({'ret': 1, 'data': '已经绑定专业,无需重复绑定!'})
            if classesBindProfession.objects.create(classesCode=classesCode, professionCode=professionCode):
                return JsonResponse({'ret': 0, 'data': '添加班级成功！'})
        else:
            return JsonResponse({'ret': 1, 'data': '添加班级失败,请稍后重试！'})


def editClasses(requestData):
    """
    修改班级名称操作函数
    :param requestData:
    :return:
    """
    if classesManage.objects.filter(classesCode=requestData['classesCode']).update(
            classesName=requestData['classesName']):
        return JsonResponse({'ret': 0, 'data': '修改班级名称成功！'})
    else:
        return JsonResponse({'ret': 1, 'data': '修改班级名称失败,请稍后重试！'})


def deleteClasses(requestData):
    """
    删除班级操作函数
    :param requestData:
    :return:
    """
    classesCode = requestData['classesCode']
    if classesManage.objects.filter(classesCode=classesCode).delete() and classesBindProfession.objects.filter(
            classesCode=classesCode).delete():
        studentManage.objects.filter(classesCode=classesCode).update(classesCode='0', professionCode='0')
        # 需要重置已绑定专业的班级还有学生
        return JsonResponse({'ret': 0, 'data': '删除班级成功！'})
    else:
        return JsonResponse({'ret': 1, 'data': '删除班级失败,请稍后重试！'})


def getclassesData(requestData):
    """
    获取班级管理页面的专业列表数据
    :param requestData:
    :return:
    """
    queryData = requestData['query']  # 查询的元数据
    keyWord = queryData['keyWord']  # 查询的关键词
    pageNum = queryData['pageNum']  # 当前页数
    pageSize = queryData['pageSize']  # 一页多少数据
    classObj = classesManage.objects

    classesData = []
    classesList = list(classObj.filter(classesName__contains=keyWord).values())
    myData = listSplit(classesList, pageSize, pageNum)  # 自定义分页(提高系统运行速度)
    for classes in myData['currentData']:
        for bind in classesBindProfession.objects.filter(classesCode=classes['classesCode']).values():
            for profession in professionManage.objects.filter(professionCode=bind['professionCode']).values():
                classes.update({'toProfession': profession['professionName']})
            studentCount = studentManage.objects.filter(classesCode=classes['classesCode']).count()
            classes.update({'classesHumanNum': studentCount})
        classesData.append(classes)

    return JsonResponse({
        'ret': 0,
        'data': classesData,
        'pageNum': pageNum,
        'total': myData['dataSum'],
    })


def getProfessionDataCascaderOptions(requestData):
    """
    获取专业数据供班级页面联动菜单使用
    :param requestData:
    :return:
    """
    data = []
    for i in professionManage.objects.values():
        data.append({'value': i['professionCode'], 'label': i['professionName']})
    return JsonResponse({'ret': 0, 'data': data})


def getProfessionAndClassesLevelDataCascaderOptions(requestData):
    """
    获取专业数据及子菜单(班级)及其对应届数供学生页面联动菜单使用
    :param requestData:
    :return:
    """

    # 合成专业数据
    global classesLevelData
    professionData = []  # 临时存放专业数据
    for i in professionManage.objects.values():
        professionCode = i['professionCode']
        professionName = i['professionName']
        professionData.append({'value': str(professionCode), 'label': professionName, 'disabled': True})

    # 提取绑定关系数据
    bindData = []
    for i in classesBindProfession.objects.values():
        for ii in classesManage.objects.values():
            if i['classesCode'] == ii['classesCode']:
                classesCode = ii['classesCode']
                classesName = ii['classesName']
                classesLevel = ii['classesLevel']
                professionCode = i['professionCode']
                bindData.append(
                    {'value': str(classesCode), 'label': classesName, 'classesLevel': classesLevel,
                     'professionCode': str(professionCode)})

    # 提取班级届数
    classesLevelList = []
    for i in bindData:
        if i['classesLevel'] not in classesLevelList:
            classesLevelList.append(i['classesLevel'])

    # 合成班级数据
    classesData = []
    for i in professionData:
        allClasses = []
        for ii in bindData:
            classesCode = ii['value']
            classesName = ii['label']
            classesLevel = ii['classesLevel']
            if i['value'] == ii['professionCode']:
                allClasses.append(
                    {'professionCode': ii['professionCode'], 'value': str(classesCode), 'label': classesName,
                     'classesLevel': classesLevel})

        # 班级届数分类
        for iii in classesLevelList:
            classes = []
            professionCode = 0
            for iiii in allClasses:
                if iii == iiii['classesLevel']:
                    professionCode = iiii['professionCode']
                    classes.append(iiii)
            classesData.append(
                {'professionCode': professionCode, 'value': iii, 'label': iii + '届', 'children': classes})

    # 合成最终数据
    professionContainer = []  # 专业容器包含班级子容器 value:专业编号 label:专业名称
    for i in professionData:
        professions = []
        for ii in classesData:
            if str(ii['professionCode']) == str(i['value']):
                i['disabled'] = False
                professions.append(ii)
        professionContainer.append(
            {'value': i['value'], 'label': i['label'], 'children': professions, 'disabled': False})

    return JsonResponse({'ret': 0, 'data': professionContainer})


def getProfessionAndClassesDataCascaderOptions(requestData):
    """
    获取专业及包含届数
    :param requestData:
    :return:
    """
    data = []
    for i in list(professionManage.objects.values()):
        professions = []
        for ii in list(classesBindProfession.objects.values()):
            if str(i['professionCode']) == str(ii['professionCode']):
                for iii in list(classesManage.objects.filter(classesCode=ii['classesCode']).values()):
                    if str(iii['classesCode']) == str(ii['classesCode']):
                        if {'value': iii['classesLevel'], 'label': iii['classesLevel'] + '届'} not in professions:
                            professions.append({'value': iii['classesLevel'], 'label': iii['classesLevel'] + '届'})
        data.append(
            {'value': i['professionCode'], 'label': i['professionName'], 'disabled': False, 'children': professions})

    return JsonResponse({'ret': 0, 'data': data})
