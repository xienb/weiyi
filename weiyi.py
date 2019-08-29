import requests
import json
import time
import pymysql
import math
import os
import logging
import _thread
from bs4 import BeautifulSoup



class weiyi(object):
    def __init__(self):
        self.baseurl='https://www.guahao.com/'
        self.jsoncity = 'json/white/area/citys?provinceId='
        self.hospitalurl='hospital/{0}/{1}/{2}/{3}/{4}'
        self.hospital_remark='hospital/introduction/{0}'
        self.hospital_detail='hospital/{0}'
        self.doctor_list_url='department/shiftcase/{0}?pageNo={1}'
        self.doctor_detail_url='expert/{0}'

        self.cookies_default=self.get_cookie()

    def get_province(self):
        #req=requests.get(self.baseurl+self.serchurl)
        #html=req.text
        #bf=BeautifulSoup(html,"html.parser")
        php='D:\PyProject\pytest\province.html'
        htmlfile = open(php, 'r', encoding='utf-8')
        htmlhandle = htmlfile.read()
        bf = BeautifulSoup(htmlhandle, "html.parser")
        texts = bf.find_all('a', class_ = 'J_ProvinceLink')
        for a in texts:
            if a['data-val']!='all':
                sql="insert into province(`id`,`name`) values("+a['data-val']+",'"+a.get_text()+"')"
                self.insert(sql)

    def get_city(self):
        pro=self.query("select * from province")
        for row in pro:
            req = requests.get(self.baseurl + self.jsoncity+str(row[0]))
            jo = json.loads(req.text)
            for city in jo:
                if city["value"]!="all":
                    sql="insert into city(`id`,`name`,`pid`,`pname`) values("+city["value"]+",'"+city["text"]+"',"+str(row[0])+",'"+str(row[1])+"')"
                    self.insert(sql)
                # print(city["value"]+city["text"])
        return

    def get_hospital(self):
        table_citys= self.query("select * from city where finish is null")
        for row in table_citys:
            try:
                city_id=row[0]
                city_name=row[1]
                province_id=row[2]
                province_name=row[3]
                req_hospital_list_first=requests.get((self.baseurl+self.hospitalurl).format(str(province_id),province_name,str(city_id),city_name,'')) #请求第一页
                bf_hospitall_list_first = BeautifulSoup(req_hospital_list_first.text,"html.parser")
                if bf_hospitall_list_first.find_all("strong", id='J_ResultNum').__len__()>0:
                    hospital_num = bf_hospitall_list_first.find_all("strong", id='J_ResultNum')[0].get_text() # 该地区医院总数
                    hospital_pages = math.ceil(float(hospital_num) / 10) #该地区医院总页数
                    if hospital_pages>100:hospital_pages=100  #最多100页，超出100无法查询数据
                    # tt=bf.find_all('form',attrs={'name':'qPagerForm'}) #find_all按属性查询
                    for i in range(1,hospital_pages):#遍历每一页
                        req_hospital_list_i=requests.get((self.baseurl+self.hospitalurl).format(str(province_id),province_name,str(city_id),city_name,'p'+str(i)))
                        bf_hospitall_list_i = BeautifulSoup(req_hospital_list_i.text, "html.parser")
                        a_hospitals = bf_hospitall_list_i.find_all('a', class_='cover-bg seo-anchor-text')
                        for a_hospital in a_hospitals:
                            hospital_code=a_hospital["monitor-hosp-id"]
                            print("正在导入医院："+hospital_code)
                            req_hospital_remark=requests.get((self.baseurl+self.hospital_remark).format(hospital_code))
                            bf_hospitall_remark= BeautifulSoup(req_hospital_remark.text,"html.parser")
                            hospitall_remark = bf_hospitall_remark.find_all("pre")[0].get_text()#医院简介

                            req_hospital_detail = requests.get((self.baseurl + self.hospital_detail).format(hospital_code))
                            bf_hospitall_detail = BeautifulSoup(req_hospital_detail.text, "html.parser")
                            base_div=bf_hospitall_detail.find("section",class_="grid-section hospital-card fix-clear").find("div",class_="info")

                            #获取医院基本信息
                            hospitall_name =base_div.find_all('strong')[0].find_all('a')[0].get_text().replace("\n","").replace("\r","").strip()
                            hospital_rank = base_div.find_all('span',class_='h3')[0].get_text().replace("\n","").replace("\r","").strip()
                            hospital_address=base_div.find_all('div',class_='address')[0].find_all('span')[0].get_text().replace("\n","").replace("\r","").strip()
                            hospital_phone = base_div.find_all('div', class_='tel')[0].find_all('span')[0].get_text().replace("\n","").replace("\r","").strip()
                            hospital_follows=bf_hospitall_detail.find_all('span',class_='mark-count')[0].get_text().replace("\n","").replace("\r","").strip()
                            hospital_appointments=''
                            hospital_evaluations=''
                            hospital_total_fix_clear = bf_hospitall_detail.find_all('div',class_='total fix-clear')
                            if hospital_total_fix_clear.__len__()>0:  #未开通挂号的医院，这两个字段没有
                                hospital_appointments=hospital_total_fix_clear[0].find_all('strong')[0].get_text().replace("\n","").replace("\r","").strip()
                                hospital_evaluations=hospital_total_fix_clear[0].find_all('strong')[1].get_text().replace("\n","").replace("\r","").strip()
                            #插入hospital表
                            sql_insert_hospital="INSERT INTO `hospital`(`cid`,`code`,`name`,`rank`,`address`,`phone`,`remarks`,`follows`,`evaluations`,`appointments`) VALUES({0},'{1}','{2}','{3}','{4}','{5}','{6}','{7}','{8}','{9}')"
                            sss=sql_insert_hospital.format(str(city_id),hospital_code,hospitall_name,hospital_rank,hospital_address,hospital_phone,hospitall_remark,hospital_follows,hospital_evaluations,hospital_appointments)
                            self.insert(sss)

                            #获取科室信息
                            bf_hospital_department_section= bf_hospitall_detail.find('section',id='departments')
                            bf_hospital_department_section_lis=bf_hospital_department_section.find_all('li',class_='g-clear')
                            for li in bf_hospital_department_section_lis:
                                department_ptype=li.find('label').get_text().replace("\n","").replace("\r","").strip()
                                bf_department_a=li.find_all('a')
                                for department_a in bf_department_a:
                                    department_code=department_a["monitor-div-id"]
                                    department_name=department_a.get_text().replace("\n","").replace("\r","").strip()
                                    # 插入department表
                                    sql_insert_department="INSERT INTO `department`(`cid`,`code`,`name`,`hcode`,`ptype`) VALUES({0},'{1}','{2}','{3}','{4}')"
                                    self.insert(sql_insert_department.format(str(city_id),department_code,department_name,hospital_code,department_ptype))
            except Exception as  e:
                #出现异常，则删除当前城市的数据并抛出异常
                self.excute("delete from department where cid=" + str(row[0]))
                self.excute("delete from hospital where cid=" + str(row[0]))
                logging.exception(e)
                os.system('pause')
                raise
            self.excute("update city set finish=1 where id="+str(row[0]))
            print(row[1]+"导入完成")
        return

    def get_doctor(self):
        table_department_list = self.query("select department.id,department.cid,department.`code`,department.`name`,department.hcode,hospital.`name` as hname from department  left join hospital on hospital.`code`=department.hcode where  department.finish is null")
        for row in table_department_list:
            try:
                department_id=str(row[0])
                city_id=str(row[1])
                department_code=row[2]
                department_name=row[3]
                hospital_code=row[4]
                hospital_name=row[5]
                req_doctor_list_first = requests.get((self.baseurl + self.doctor_list_url).format(department_code,"1"))
                bf_doctor_list_first = BeautifulSoup(req_doctor_list_first.text,"html.parser")
                if bf_doctor_list_first.find_all("strong", id='J_ResultNum').__len__() > 0:
                    doctor_num = bf_doctor_list_first.find_all("strong", id='J_ResultNum')[0].get_text().replace("\n","").replace("\r","").strip()
                    doctor_pages = math.ceil(float(doctor_num) / 12)
                    if doctor_pages > 10: doctor_pages = 10
                    for i in range(1, doctor_pages):#遍历每一页
                        req_doctor_list_i=requests.get((self.baseurl+self.doctor_list_url).format(department_code,str(i)))
                        bf_doctor_list_i = BeautifulSoup(req_doctor_list_i.text, "html.parser")
                        div_doctors = bf_doctor_list_i.find_all('div', class_='g-doctor-item2 g-clear to-margin')
                        for div_doctor in div_doctors:
                            a_doctor=div_doctor.find("a",class_='name js-doc')
                            a_doctor_href=a_doctor["href"]
                            index_start=a_doctor_href.index('/expert/')+8
                            index_end=a_doctor_href.index('?')
                            doctor_code=a_doctor_href[index_start:index_end]
                            print("医生编码："+doctor_code)
                            #doctor_dep表直接增加
                            #doctor表，先判断数据库中是否有，有则跳过，无则访问医生主页（一个医生可跨多个科室）
                            sql_insert_doctor_dep = "INSERT INTO `doctor_dep`(`doc_code`,`dep_code`,`dep_name`,`hos_code`,`hos_name`) VALUES('{0}','{1}','{2}','{3}','{4}')"
                            self.insert(sql_insert_doctor_dep.format(doctor_code, department_code, department_name,hospital_code, hospital_name))

                            d_count=len(self.query("select * from doctor where code='"+doctor_code+"'"))
                            if(d_count==0):
                                req_doctor_detail=requests.get((self.baseurl+self.doctor_detail_url).format(doctor_code))
                                bf_doctor_detail=BeautifulSoup(req_doctor_detail.text, "html.parser")
                                div_doctor_detail_base=bf_doctor_detail.find("div",class_="grid-section expert-card fix-clear")
                                if div_doctor_detail_base!=None: #根据code访问医生主页有可能不存在
                                    doctor_name=div_doctor_detail_base.find("strong",class_="J_ExpertName").get_text().replace("\n","").replace("\r","").strip()
                                    span_title_list=div_doctor_detail_base.find("div",class_="detail word-break").find("h1").find_all("span")
                                    doctor_title=''
                                    for span_tile in span_title_list:
                                        if span_tile.get_text()!="点赞": #过滤点赞的span
                                            doctor_title+=span_tile.get_text()
                                    doctor_follows=div_doctor_detail_base.find("span",class_="mark-count").get_text().replace("\n","").replace("\r","").strip()
                                    a_keys_list=div_doctor_detail_base.find("div",class_="keys").find_all("a")
                                    key_list=[]
                                    for one_keys in a_keys_list:
                                        key_list.append(one_keys["title"])
                                    doctor_keys= ','.join(key_list)
                                    doctor_goodat=""
                                    if div_doctor_detail_base.find("div",class_="goodat").find("a")==None:
                                        if div_doctor_detail_base.find("div", class_="goodat").find("span")!=None:
                                            doctor_goodat = div_doctor_detail_base.find("div", class_="goodat").find("span").get_text()
                                    else:
                                        doctor_goodat = div_doctor_detail_base.find("div", class_="goodat").find("a")["data-description"]
                                    doctor_about=""
                                    if div_doctor_detail_base.find("div",class_="about").find("a")==None:
                                        if  div_doctor_detail_base.find("div", class_="about").find("span")!=None:
                                            doctor_about = div_doctor_detail_base.find("div", class_="about").find("span").get_text()
                                    else:
                                        doctor_about = div_doctor_detail_base.find("div", class_="about").find("a")["data-description"]
                                    doctor_rate=''
                                    if div_doctor_detail_base.find("div",id="expert-rate")!=None and div_doctor_detail_base.find("div",id="expert-rate").find("strong")!=None:
                                        doctor_rate=div_doctor_detail_base.find("div",id="expert-rate").find("strong").get_text().replace("\n","").replace("\r","").strip()
                                    doctor_yy=''
                                    doctor_wz=''
                                    if div_doctor_detail_base.find("div",class_="total fix-clear")!=None and len(div_doctor_detail_base.find("div",class_="total fix-clear").find_all("strong"))>1:
                                        doctor_yy=div_doctor_detail_base.find("div",class_="total fix-clear").find_all("strong")[0].get_text().replace("\n","").replace("\r","").strip()
                                        doctor_wz=div_doctor_detail_base.find("div",class_="total fix-clear").find_all("strong")[1].get_text().replace("\n","").replace("\r","").strip()
                                    doctor_commenturl="empty"
                                    if bf_doctor_detail.find("a",attrs={'monitor':'doctor,doctor_rate,rate_more'})!=None:
                                        doctor_commenturl=bf_doctor_detail.find("a",attrs={'monitor':'doctor,doctor_rate,rate_more'})["href"]
                                    sql_insert_doctor="INSERT INTO `doctor`(`code`,`name`,`title`,`follows`,`keys`,`goodat`,`about`,`rate`,`yy`,`wz`,`commenturl`) VALUES('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}','{8}','{9}','{10}')"
                                    self.insert(sql_insert_doctor.format(doctor_code,doctor_name,doctor_title,doctor_follows,doctor_keys,doctor_goodat,doctor_about,doctor_rate,doctor_yy,doctor_wz,doctor_commenturl))
                                    print("增加医生："+doctor_name)

            except Exception as e:
                table_need_delete=self.query("SELECT * FROM doctor_dep where dep_code='"+row[2]+"'")
                for need_delete_row in table_need_delete:
                    self.excute("delete from doctor_dep where id=" + str(need_delete_row[0]))
                    self.excute("delete from doctor where code='"+need_delete_row[1]+"'")
                logging.exception(e)
                os.system('pause')
                raise
            self.excute("update department set finish=1 where id="+str(row[0]))
            print(str(row[0])+"导入完成")
        return

    def get_comments(self):
        table_doctor_list = self.query("select * from doctor where finish=2")#commenturl is null兼容未获取commenturl的老数据
        #pages = math.ceil(len(table_doctor_list) / 10)
        l=len(table_doctor_list)
        print("总长："+str(l))
        self.get_comments_thread(table_doctor_list)
        # num_per_thread=4000
        # current_start=0
        # while True:
        #     current_end=current_start+num_per_thread
        #     if current_end>=l:current_end=l
        #     _thread.start_new_thread(self.get_comments_thread,(table_doctor_list[current_start:current_end],))
        #     if current_end==l:break
        #     else: current_start=current_end
        return
    def get_comments_thread(self,tup):
        for row in tup:
            try:
                doctor_commenturl = "empty"
                if row[11]==None or row[11]=='':#commenturl为空，先获取commenturl
                    req_doctor_detail = requests.get((self.baseurl + self.doctor_detail_url).format(row[1]))
                    bf_doctor_detail = BeautifulSoup(req_doctor_detail.text, "html.parser")
                    div_doctor_detail_base = bf_doctor_detail.find("div", class_="grid-section expert-card fix-clear")
                    if div_doctor_detail_base != None:  # 根据code访问医生主页有可能不存在
                        if bf_doctor_detail.find("a", attrs={'monitor': 'doctor,doctor_rate,rate_more'}) != None:
                            doctor_commenturl = bf_doctor_detail.find("a", attrs={'monitor': 'doctor,doctor_rate,rate_more'})["href"]
                    #更新一下commenturl字段
                    sql_update_doctor_commenturl = "update doctor set commenturl='{0}' where id={1}"
                    self.excute(sql_update_doctor_commenturl.format(doctor_commenturl,str(row[0])))
                else:
                    doctor_commenturl = row[11]
                doctor_code=row[1]
                #开始访问患者评论页面
                if doctor_commenturl!='empty':#处理有评论的医生
                    #print(doctor_commenturl)
                    req_doctor_commenturl=requests.get(doctor_commenturl)
                    bf_doctor_commenturl =  BeautifulSoup(req_doctor_commenturl.text, "html.parser")
                    div_comment_filter = bf_doctor_commenturl.find("div",id="comment-filter")
                    if div_comment_filter!=None:
                        li_class_impression_list = div_comment_filter.find_all("li",class_="impression");
                        impression_list=[]
                        for one_impression in li_class_impression_list:
                            impression_list.append(one_impression.get_text().replace("\n","").replace("\r","").strip())
                        doctor_impression=','.join(impression_list)
                        doctor_disease=''
                        ul_class_container_fix_clear_comment_container = div_comment_filter.find("ul",class_="container fix-clear comment-container")
                        if ul_class_container_fix_clear_comment_container!=None:
                            a_ul_class_container_fix_clear_comment_container=ul_class_container_fix_clear_comment_container.find_all("a")
                            disease_list=[]
                            for one_disease in a_ul_class_container_fix_clear_comment_container:
                                if one_disease.get_text()!="全部":
                                    disease_list.append(one_disease.get_text())
                            doctor_disease = ','.join(disease_list)
                            #更新doctor表
                            sql_update_doctor_im_di="update doctor set impression='{0}',disease='{1}' where id={2} "
                            self.excute(sql_update_doctor_im_di.format(doctor_impression,doctor_disease,str(row[0])))

                    #处理评论流程
                    print("处理评论流程")
                    self.get_one_comments(doctor_commenturl,doctor_code)
            except Exception as e:
                self.excute("delete from comments where doctor_code='"+row[1]+"'")
                self.excute("update doctor set finish=2 where id=" + str(row[0]))  #标记finish=2表示出错的记录
                logging.exception(e)
                print("导入出错，doctor_code："+row[1])
                # os.system('pause')
                # raise
                continue
            self.excute("update doctor set finish=1 where id="+str(row[0]))
            print("导入完成，doctor_code："+row[1])

    def get_one_comments(self,doctor_commenturl,doctor_code):
        req_doctor_commenturl = requests.get(doctor_commenturl,cookies=self.cookies_default)
        bf_doctor_commenturl = BeautifulSoup(req_doctor_commenturl.text, "html.parser")
        span_class_tip = bf_doctor_commenturl.find("span",class_="tip")
        if span_class_tip!=None:
            comment_number = span_class_tip.find("strong").get_text()
            comment_pages =  math.ceil(float(comment_number) / 5)
            if comment_pages > 60: comment_pages = 60
            comment_page_format_url=doctor_commenturl.replace("1-0","all-0")+"?pageNo={0}&sign={1}&timestamp={2}"
            #保存第一页的评价数据
            self.save_comment(bf_doctor_commenturl,doctor_code)
            if comment_pages>1:
                sign = bf_doctor_commenturl.find("input", attrs={'name': 'sign'})["value"]
                timestamp = bf_doctor_commenturl.find("input", attrs={'name': 'timestamp'})["value"]
                for page in range(2,comment_pages+1):
                    print(page)
                    new_url= comment_page_format_url.format(page,sign,timestamp)
                    req_comment_page=requests.get(new_url,cookies=self.cookies_default)
                    bf_comment_page= BeautifulSoup(req_comment_page.text, "html.parser")
                    sign = bf_comment_page.find("input", attrs={'name': 'sign'})["value"]  #更新sign
                    timestamp = bf_comment_page.find("input", attrs={'name': 'timestamp'})["value"]  #更新timestamp

                    #保存当前页的数
                    self.save_comment(bf_comment_page,doctor_code)
        return

    def save_comment(self,bf_comment_page,doctor_code):
        div_comment_list = bf_comment_page.find("ul",id="comment-list")
        if div_comment_list!=None:
            lis_div_comment_list=div_comment_list.find_all("li")
            for li in lis_div_comment_list:
                p_name=li.find("div",class_="user").find("p").get_text().replace("\n","").replace("\r","").replace("\t","").strip()
                satisfaction=""
                if li.find("div",class_="row-1").find("p",class_="attitude")!=None and li.find("div",class_="row-1").find("p",class_="attitude").find("strong")!=None:
                    satisfaction=li.find("div",class_="row-1").find("p",class_="attitude").find("strong").get_text().replace("\n","").replace("\r","").replace("\t","").strip()
                disease=""
                if li.find("div",class_="row-1").find("p",class_="disease")!=None and li.find("div",class_="row-1").find("p",class_="disease").find("span")!=None:
                    disease=li.find("div",class_="row-1").find("p",class_="disease").find("span").get_text().replace("\n","").replace("\r","").strip()
                evaluation=""
                if li.find("div",class_="row-2").find("span",class_="summary")!=None:
                    evaluation=li.find("div",class_="row-2").find("span",class_="summary").get_text().replace("\n","").replace("\r","").strip()
                e_time=""
                from_=""
                if li.find("div",class_="row-2").find("div",class_="info")!=None and len(li.find("div",class_="row-2").find("div",class_="info").find_all("span"))>1:
                    e_time=li.find("div",class_="row-2").find("div",class_="info").find_all("span")[0].get_text().replace("\n","").replace("\r","").strip()[:19]
                    from_=li.find("div",class_="row-2").find("div",class_="info").find_all("span")[1].get_text().replace("\n","").replace("\r","").replace("    ","").strip()[3:] #去掉制表符
                # print(doctor_code)
                # print(p_name)
                # print(satisfaction)
                # print(disease)
                # print(evaluation)
                # print(e_time)
                # print(from_)
                sql_insert_comment="INSERT INTO `comments`(`doctor_code`,`p_name`,`satisfaction`,`disease`,`evaluation`,`e_time`,`from`) VALUES('{0}','{1}','{2}','{3}','{4}','{5}','{6}')"
                self.insert(sql_insert_comment.format(doctor_code,p_name,satisfaction,disease,evaluation,e_time,from_))
        return

    def get_cookie(self):
        cookies = "_sid_=1565070627998018725013171; _fp_code_=4677d0eebacc4299fb14b4b34423e8fd; _fm_code=e3Y6ICIyLjUuMCIsIG9zOiAid2ViIiwgczogMTk5LCBlOiAianMgbm90IGRvd25sb2FkIn0%3D; _ipgeo=province%3A%E5%85%A8%E5%9B%BD%7Ccity%3A%E4%B8%8D%E9%99%90; _fo_opt=province%3A24%7Ccity%3A552%7Chospital%3A%7Chdid%3A; searchHistory=%E6%B9%96%E5%8D%97%E7%9C%81%E8%A1%A1%E9%98%B3%E5%B8%82%E8%A1%A1%E5%8D%97%E5%8E%BF%E6%B3%89%E6%B9%96%E9%95%87%E5%BB%BA%E4%BC%9F%E6%9D%91%E5%8D%AB%E7%94%9F%E5%AE%A4%2C%7C%E5%A4%A9%E6%B2%B3%E5%8C%BA%E7%9F%B3%E7%89%8C%E8%A1%97%E5%8D%8E%E5%B8%88%E7%A4%BE%E5%8C%BA%E5%8D%AB%E7%94%9F%E6%9C%8D%E5%8A%A1%E4%B8%AD%2C%7C%E4%B8%AD%E5%8C%BB%E7%A7%91%2C%7C%2Cclear; _e_m=1565574369350; _area_=%7B%22provinceId%22%3A%2229%22%2C%22cityId%22%3A%2279%22%2C%22cityName%22%3A%22%E5%B9%BF%E5%B7%9E%22%2C%22provinceName%22%3A%22%E5%B9%BF%E4%B8%9C%22%7D; _fo_area_=%7B%22provinceId%22%3A%2229%22%2C%22cityId%22%3A%2279%22%2C%22cityName%22%3A%22%E5%B9%BF%E5%B7%9E%22%2C%22provinceName%22%3A%22%E5%B9%BF%E4%B8%9C%22%7D; monitor_sid=33; mst=1565675923106; __rf__=BBC+GlPyp+kTGmK3hGP3imbN2C41+jue0m3gfDahRowv20xxtBAXFYHewJf9+V0DJv4ufDGokCLTaUvtgwZrE6OA/mhyB51DgdVVLjC43O0JKxu2GholMN+RtI6firSF; JSESSIONID=dy47yxa8vvhk5uztenpjkhz3; _ci_=FsxKua9hHwbPDjN0VMqqf29xubd3T7xk05Ch5+Iq9L5NGoT5vPmVhY7Jn8L9dsbm; __i__=KY+7se9fHQmA81CoMrW/5H9AsPuSAo4aAoV/liI/XM0=; __uiu__=mRA0rpsPlq8oDODLoJfRAje/y7jNP/Xc1+qqU+wmtqSo0ZktWbgVTg==; __usx__=PUeI65mvElhEFV6otLbHrl0wM3IETjK0uI0iaOjuuhU=; __up__=c/3ILu5BUsopvYjP7Ecbd925vhQnZhRE2DBwZnEEFYo=; _exp_=tBzbsq4V55eovoIBVJSowVg3rqhN3E6l86IPFhUfYxU=; __p__=YVeao5vPSezUhcpY+KjsyCveAc61r+AlPzrff5CPFgqGI+eldiEg0Q==; __uli__=DCduqCAQTpTAHdChD+1ghHNgncE/bYiIUmeqnDLGfz1HwZAuPF/XIfkxOV0wYPRLomxmcdlJpITF8UsrCnonrV0tMpfmm468Qs95HCJU7jg4yP2sgN9r3Q==; __un__=4dMOfWbKAsM1il08piQ5VrYTQJEeyw5jFVmKokiLAs8jokgN7ae2q+UPCANSiti1n+dm7EcMhGM=; __wyt__=!PFKywWCeYQUXsUlz_Xvm8fmEdYU9V1PU3DMp2JGNIyACXEQiuXoVYu8ZIBfN9eDAOaT1ogs4Fy3v_YBNWKnZ5j4tus1q-ixkDCLsmEGIA-7PRXUMJG-6ChkCHOE2AKqRBScSMvtaV9mtD9CIBgJ5TDBLBPRC-GQkgXfrsK03Y4Wio; monitor_seq=49; mlt=1565679103110"
        dic={}
        for i in cookies.split(';'):
            dic[i.split("=")[0].strip()]=i.split("=")[1]
        return dic

    def insert(self,sql):
        db = pymysql.connect("192.168.88.188", "root", "123456", "guahao")
        # 使用cursor()方法获取操作游标
        cursor = db.cursor()
        try:
            cursor.execute(sql)
            db.commit()
        except:
            db.rollback()
        db.close()

    def query(self,sql):
        db = pymysql.connect("192.168.88.188", "root", "123456", "guahao")
        cursor = db.cursor()
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
        except:
            print("Error: unable to fecth data")
        db.close()
        return results

    def excute(self,sql):
        db = pymysql.connect("192.168.88.188", "root", "123456", "guahao")
        cursor = db.cursor()
        try:
            cursor.execute(sql)
            db.commit()
        except:
            db.rollback()
        db.close()
        return

wy= weiyi()
#wy.get_province() #获取省份
#wy.get_city()  #获取城市
#wy.get_hospital()#获取医院
#wy.get_doctor() #获取医生
#wy.get_one_comments("https://www.guahao.com/commentslist/e-7baf3915-8bf9-4143-9621-02b31f1d59dc000/1-0","test-code")
wy.get_comments()#获取评价
#wy.get_cookie()



