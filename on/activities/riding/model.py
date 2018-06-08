from django.db import models
import uuid
from on.activities.base import Goal, Activity
from on.user import UserInfo, UserTicket, UserRecord, UserSettlement, BonusRank
import django.utils.timezone as timezone
from django.conf import settings
import os
import pytz
import math
from datetime import timedelta, datetime
import decimal
from logging import getLogger

logger = getLogger("app")


class RidingGoalManager(models.Manager):
	# 创建一个新的goal
	def create_goal(self, user_id, runningtype, guaranty, down_payment, activate_deposit, coefficient, mode, goal_day,
	                distance, average, nosign, extra_earn, reality_price, deserve_price, punch_day, down_num):
		running_type = 0 if runningtype == "FREE" else 1
		if settings.DEBUG:
			start_time = timezone.now()
		else:
			# 当天创建活动只有后一天才能参加，所以以后一天为开始日期
			start_time = timezone.now()  # + timedelta(days=1)
		# start_time = datetime.strptime("2018-01-01 00:00:01", "%Y-%m-%d %H:%M:%S")
		kilos_day, goal_distance, left_distance = None, None, None
		if running_type:
			kilos_day = distance
		else:
			actual_day_map = {
				7: 6,
				14: 12,
				21: 18,
				30: 25,
				61: 50
			}
			goal_distance = distance
			left_distance = distance
			distances = int(distance)
			kilos_day = 2 * distances // actual_day_map[goal_day]
		# 查询出没有支付的活动
		goal = self.filter(user_id=user_id).filter(start_time=start_time).filter(status="PENDING")
		# 如果存在的话就删掉
		if goal:
			goal.first().delete()
		goal = self.create(user_id=user_id,
		                   activity_type=RidingGoal.get_activity(),
		                   start_time=start_time,
		                   goal_day=goal_day,
		                   mode=mode,
		                   guaranty=guaranty,
		                   down_payment=down_payment,
		                   activate_deposit=activate_deposit,
		                   coefficient=coefficient,
		                   goal_type=running_type,
		                   goal_distance=goal_distance,
		                   left_distance=left_distance,
		                   kilos_day=kilos_day,
		                   extra_earn=extra_earn,
		                   average=average,
		                   reality_price=reality_price,
		                   deserve_price=deserve_price,
		                   punch_day=0,
		                   down_num=down_num
		                   )
		# 更新活动的免签卡券

		if running_type:
			nosgin_number = int(nosign)
			UserTicket.objects.create_ticket(goal.goal_id, "NS", nosgin_number)
		return goal

	def create_ridinggoal(self, user_id, start_time, goal_type, guaranty, down_payment, activate_deposit, coefficient,
	                      mode, goal_day, deduction_point, deduction_guaranty, goal_distance,
	                      reality_price, deserve_price, down_num, kilos_day, multiple):
		goal = self.create(user_id=user_id,
		                   activity_type=RidingGoal.get_activity(),
		                   start_time=start_time,
		                   goal_day=goal_day,
		                   mode=mode,
		                   guaranty=guaranty,
		                   down_payment=down_payment,
		                   activate_deposit=activate_deposit,
		                   coefficient=coefficient,
		                   goal_type=goal_type,
		                   goal_distance=goal_distance,
		                   left_distance=goal_distance,
		                   kilos_day=kilos_day,
		                   average=10,
		                   reality_price=reality_price,
		                   deserve_price=deserve_price,
		                   down_num=down_num,
		                   multiple=multiple,
		                   deduction_guaranty=deduction_guaranty,
		                   deduction_point=deduction_point,
		                   )
		return goal

	# 删除一个目标
	def delete_goal(self, goal_id):
		goal = self.get(goal_id=goal_id)
		# 删除本目标对应的所有打卡记录
		goal.punch.all().delete()
		# 删除本目标
		goal.delete()

	# 用户每一次打卡成功后就加一
	def update_punch(self, goal_id):
		record = self.get(goal_id=goal_id)
		record.punch_day += 1
		record.save()

	# 当用户结算的时候将用户的打卡记录改成0
	def clear_punch(self, goal_id):
		record = self.get(goal_id=goal_id)
		record.punch_day += 1
		record.save()


class RidingGoal(Goal):
	""" Model for running goal
		User needs to set running duration days and distance as
		objective
	"""
	# 目标距离
	goal_distance = models.FloatField(null=True)
	# 单日目标距离，对于自由模式来说，kilos_day为单日目标上限
	kilos_day = models.FloatField(null=True)
	# 剩余距离, 只针对自由模式有效
	left_distance = models.FloatField(null=True, default=0)
	# 用户实际要付出的金额
	reality_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
	# 用户应该要付出的金额
	deserve_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
	# 扣完底金需要的次数
	down_num = models.IntegerField(default=1, null=False)
	# 平均每次要扣的
	average = models.DecimalField(max_digits=12, decimal_places=2, null=False)
	# 活动押金
	activate_deposit = models.DecimalField(max_digits=12, decimal_places=2, null=False)
	# 累计距离,只对自由模式有效
	add_distance = models.FloatField(default=0, null=True)
	# 活动额外收益
	extra_earn = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
	punch_attention = models.IntegerField(null=False, default=1)
	is_no_use_point = models.IntegerField(null=False, default=0)
	deduction_point = models.IntegerField(null=False, default=0)
	deduction_guaranty = models.IntegerField(null=False, default=0)
	multiple = models.IntegerField(null=False, default=0)
	# 这一周累计跑的距离数
	week_distance = models.FloatField(null=False, default=0)
	# 日常模式完成的天数
	finish_week_day = models.IntegerField(null=False, default=0)
	# 用户打卡的天数
	punch_day = models.IntegerField(null=False, default=0)
	objects = RidingGoalManager()

	@staticmethod
	def get_start_date():
		return datetime.strptime("00:01", "%H:%M").time()

	@property
	def first_day_record(self):
		start_time = self.start_time.strftime("%Y-%m-%d")
		user_end_time = (self.start_time + timedelta(days=1)).strftime("%Y-%m-%d")
		if len(RidingPunchRecord.objects.filter(goal_id=self.goal_id,
		                                        record_time__range=(start_time, user_end_time))) > 0:
			return True
		else:
			return False

	# 由于是用户不需要投一天参加第二天开始，所以不需要riqi
	def earn_riding_profit(self, average_pay):
		print("开始分配奖金")
		'''获取系数对象'''

		ridingCoeff = RidingCoefficient.objects.get(user_id=self.user_id)
		coefficient = 1
		if ridingCoeff.new_coeff:
			coefficient = ridingCoeff.new_coeff
		else:
			coefficient = ridingCoeff.default_coeff

		if self.status == "ACTIVE" or self.status == "DEALWITH":
			earn_pay = math.floor((average_pay * self.coefficient) * 100) / 100
			self.bonus += decimal.Decimal(earn_pay)
			self.save()
			try:
				rank = BonusRank.objects.filter(user_id=self.user_id)
				if rank:
					BonusRank.objects.add_ride(user_id=self.user_id, profit=earn_pay)
				else:
					BonusRank.objects.create(user_id=self.user_id, ride=earn_pay)
			except Exception as e:
				logger.error(e)
			# 修改用户赚得的总金额
			UserInfo.objects.update_balance(user_id=self.user_id, pay_delta=earn_pay)

			# 在settlement表中增加记录
			UserSettlement.objects.earn_profit(self.goal_id, decimal.Decimal(earn_pay))
			if self.status == "DEALWITH":
				self.status = "FAILED"
				self.save()

	def calc_pay_out(self):
		print("计算开始..........")
		pay_out = 0
		# 如果是日常模式
		if self.goal_type == 1:
			# 如果之前没有过不良记录, 则扣除保证金
			if self.none_punch_days == 0:
				pay_out = self.guaranty
				print(pay_out, '如果之前没有过不良记录, 则扣除保证金，扣除金额就是保证金的数量')
				# 清除个人的保证金数额
				self.guaranty = 0
				print("将保证金改为0")
				# 增加不良记录天数
				self.none_punch_days = 1
			elif self.none_punch_days >= 1 and self.down_payment > 0:
				print("如果不良天数不等于1")
				if self.guaranty == 0:
					# 底金次数
					pay_out = self.average
					print(pay_out, "当保证金等于0的时候需要扣除的底金金额")
				# 如果有降低投入
				# 从账户中扣除金额
				self.down_payment -= pay_out
				print("扣除之后需要将用户的底金减去")
				# 不良天数记录+1
				self.none_punch_days += 1
		# 如果是自由模式
		else:
			print("若是自由模式，开始扣款")
			if float(self.left_distance) > 0.0:
				print("当剩余距离大于0的时候才开始扣款")
				# 剩余的距离
				left_distance = self.left_distance
				# 求解剩余距离
				if left_distance <= 1:
					pay_out = self.guaranty
					print("当剩余的距离小于1的时候，直接扣除用户的保证金{}".format(self.guaranty))
					self.guaranty = 0
				else:
					remain = math.floor(self.left_distance) - 1
					print("剩余的距离减去1是：{}".format(remain))
					if remain <= self.down_num:
						print(type(remain), type(self.down_num), "remain:{},down_num{}".format(remain, self.down_num))
						print("走这里就对了")
						pay_out = remain * self.average + self.guaranty
						self.guaranty = 0
						print("用户的剩余距离减去1之后的距离数{}".format(math.floor(self.left_distance) - 1),
						      "平均需要扣除的金额{}".format(self.average))
						self.down_payment -= remain * self.average
					else:
						# remain = self.down_num
						print("若剩余距离大于底金次数，那么剩余距离{}".format(remain))
						pay_out = self.down_payment + self.guaranty

						self.guaranty = 0
						print("用户的剩余距离减去1之后的距离数{}".format(math.floor(self.left_distance) - 1),
						      "平均需要扣除的金额{}".format(self.average))

						self.down_payment = 0
			else:
				pay_out = 0
				print("当剩余的距离大于零的时候，需要付出的金额就是保证金")
		if pay_out > 0:
			# 更新值
			self.save()
			# 把本次瓜分金额写入数据库记录中
			UserSettlement.objects.loose_pay(goal_id=self.goal_id, bonus=pay_out)
			print("瓜分记录写入成功")
		# 完成所有瓜分金额的计算
		return pay_out

	def riding_pay_out(self):
		try:
			pay_out = 0
			# 如果是日常模式
			if self.goal_type:
				if self.none_punch_days <= 3:
					pay_out = 0
				elif self.none_punch_days == 4:
					pay_out = self.guaranty
					self.guaranty = 0
				elif self.none_punch_days >= 5 and self.down_payment > 0:
					self.guaranty = 0
					pay_out = self.average
					self.down_payment -= pay_out
			# 进入自由模式
			else:
				if self.goal_day < 30:
					if self.left_distance > 0:
						pay_out = self.guaranty
						self.guaranty = 0
				else:
					# 此时就是无线模式
					if self.left_distance > 0:
						if self.guaranty > 0:
							pay_out = self.guaranty
							self.guaranty = 0
						elif self.guaranty == 0 and self.down_payment > 0:
							pay_out = self.average
							self.down_payment -= pay_out
			if pay_out > 0:
				# 更新值
				self.save()
				# 把本次瓜分金额写入数据库记录中
				UserSettlement.objects.loose_pay(goal_id=self.goal_id, bonus=pay_out)
				print("瓜分记录写入成功")
			# 完成所有瓜分金额的计算
			return pay_out

		except Exception as e:
			print(e)

	def data_init(self):
		try:
			if self.get_remainder == True:
				self.none_punch_days = 0
				self.add_distance = 0
				self.left_distance = self.goal_distance
				self.finish_week_day = 0
				self.save()
				print("初始化成功")
			else:
				print("还没到初始化的时候")
				pass
		except Exception as e:
			logger.error(e)
			print("初始化失败")

	def check_riding(self):
		try:
			pay_out = 0
			# 用户的系数不是从活动表里面取出来，现在是在
			coeff = RidingCoefficient.objects.get(user_id=self.user_id)
			new_coeff = coeff.new_coeff
			# 只有处于活动状态的目标才会检查
			if self.status == "ACTIVE":
				# 如果是日常模式, 才会需要每天扣钱
				if self.goal_type:
					if self.goal_day < 30:
						print("进入日常模式，开始扣除金额，当前的活动类型是{}".format(self.goal_type))
						# 查看前一天到今天是否存在打卡记录
						if self.exist_punch_last_day():
							# 如果存在打卡记录,则不付出钱
							if self.left_day < 0:
								print("日常模式的剩余天数小于零，说明活动结束")
								if self.down_payment <= 0 and self.guaranty <= 0:
									self.status = "DEALWITH"
									print("押金保证金都小于0，表示失败")
								else:
									self.status = "SUCCESS"
									print("押金保证金都大于0，表示成功")
							else:
								pass
						else:
							# 如果不存在打卡记录
							if self.is_first_day:
								print("今天是第一天，不做任何处理")
								# 有返回值的时候是第一天，直接pass
								pass
							else:
								# 如果有券,则用券,不扣钱; 如果没有券,则扣除一定金额
								has_ticket = self.auto_use_ticket(ticket_type="NS")
								if not has_ticket:
									pay_out = self.riding_pay_out()
									self.none_punch_days += 1
									coeff.new_coeff = 0
									new_coeff = coeff.default_coeff
									print(pay_out, "若是日常模式且没有免签券，则扣除此金额")
								if self.down_payment <= 0 and self.guaranty <= 0:
									self.status = "DEALWITH"
									print("押金保证金都小于0，表示失败")
								# 检查目标是否已经算失败了, 在日常模式下如果两者均为0, 则判定目标失败
								if self.left_day < 0:
									print("日常模式的剩余天数小于零，说明活动结束")
									if self.down_payment <= 0 and self.guaranty <= 0:
										self.status = "DEALWITH"
										print("押金保证金都小于0，表示失败")
									else:
										self.status = "SUCCESS"
										print("押金保证金都大于0，表示成功")
					else:
						print("进入日常模式的无限模式")
						if self.exist_punch_last_day():
							"""查看前一天是否有打卡记录，若是有的话直接pass"""
							pass
						else:
							if self.is_first_day:
								print("今天是第一天，不做任何处理")
								# 有返回值的时候是第一天，直接pass
								pass
							else:
								"""不是第一天"""
								has_ticket = self.auto_use_ticket(ticket_type="NS")
								if not has_ticket:
									if not has_ticket:
										pay_out = self.riding_pay_out()
										# todo 当天系数清零
										coeff.new_coeff = 0
										new_coeff = coeff.default_coeff
										self.none_punch_days += 1
										print(pay_out, "若是日常模式且没有免签券，则扣除此金额")
								if self.down_payment <= 0 and self.guaranty <= 0:
									self.status = "DEALWITH"
									print("押金保证金都小于0，表示失败")
						# todo
						# 若是余数为0，则说明到了下一个星期，未打卡天数需要重新开始计算
						if self.get_remainder:
							self.none_punch_days = 0

				else:
					print("进入自由模式，开始扣除金额，当前的活动类型是{}".format(self.goal_type))
					# 如果是自由模式下，当left_day为负数时结算
					if self.exist_punch_last_day():
						"""查看前一天是否有打卡记录，若是有的话直接pass"""
						pass
					else:
						# 若是昨天没有打卡记录，则把信息数初始化成默认系数
						coeff.new_coeff = coeff.default_coeff
						new_coeff = coeff.default_coeff
						self.none_punch_days += 1

					if self.goal_day < 30:
						if self.left_day < 0:
							if self.guaranty == 0:
								self.status = "DEALWITH"
							else:
								self.status = "SUCCESS"
						else:
							pass
						if self.get_remainder == True:
							pay_out = self.riding_pay_out()

						print(pay_out, "用户{}自由模式下要扣除的金额数{}".format(self.user_id, pay_out))
					# 如果付出的钱没有总金额多,算完成,否则算失败
					else:
						if self.get_remainder == True:
							pay_out = self.riding_pay_out()
						print(pay_out, "用户{}自由模式下要扣除的金额数{}".format(self.user_id, pay_out))
						# 如果付出的钱没有总金额多,算完成,否则算失败
						if self.guaranty == 0 and self.down_payment == 0:
							self.status = "DEALWITH"

				# 更新到数据库中
				self.data_init()
				self.save()
				coeff.save()
				UserInfo.objects.update_deposit(user_id=self.user_id, pay_delta=-pay_out)

				return pay_out, coeff.new_coeff
		except Exception as e:
			print(e)
			logger.error(e)
			return 0, 0

	"""first_day_record"""

	@property
	def get_remainder(self):
		remainder = (timezone.now() - self.start_time).days
		if self.first_day_record:
			remain = (remainder + 1) % 7
		else:
			remain = remainder % 7
		if remain == 0:
			return True
		else:
			return False

	@staticmethod
	def get_activity():
		return "4"

	def update_activity(self, user_id):
		# 更新该种活动的总系数
		Activity.objects.add_bonus_coeff(RidingGoal.get_activity(), self.guaranty + self.down_payment,
		                                 self.coefficient)
		# 增加用户的累计参加次数
		UserRecord.objects.update_join(user=UserInfo.objects.get(user_id=user_id), coeff=self.coefficient)

	def update_activity_person(self):
		Activity.objects.update_person(RidingGoal.get_activity())
		Activity.objects.update_coeff(RidingGoal.get_activity(), -self.coefficient)


# TODO
class RidingPunchRecordManager(models.Manager):
	# 创建一个新的record
	def create_riding_redord(self, goal, user_id, voucher_ref, voucher_store, distance, record_time, document):
		print("开始打卡", goal.goal_type)
		try:
			if goal.goal_type:
				print("若是日常模式", distance, goal.kilos_day)
				if distance >= goal.kilos_day:
					print("日常模式的打卡必须是大于自己设置的每日距离")
					# 若是距离大于每日距离，求出超出的距离数量
					goal.finish_week_day += 1
					if goal.finish_week_day >= 7:
						goal.finish_week_day = 7
					# goal.left_distance -= distance
					goal.week_distance += distance
					goal.add_distance += distance
					beyond_distance = math.floor(distance - goal.kilos_day)
					print('系数更新')

					RidingCoefficient.objects.update_daily(user_id=user_id, beyond_distance=beyond_distance,
					                                       finish_week_day=goal.finish_week_day)

					goal.punch_day += 1
					goal.save()
					print('更新完成')
				else:
					print("打卡距离没有超过自己的每日距离，所以没有系数加成，新系数等于默认系数")
					RidingCoefficient.objects.defaultTonew(user_id=user_id, goal_id=goal.goal_id)
			else:
				'''进入自由模式'''
				# 先将距离加进表里面的累计距离跟周距离
				print("开始自由模式打卡")
				goal.add_distance += distance
				goal.week_distance += distance
				goal.left_distance -= distance
				if goal.left_distance < 0:
					goal.left_distance = 0
				goal.punch_day += 1
				goal.save()
				print("累计距离增加成功")
				# 若是累计的周距离大于目标距离,求出超出了多少距离
				if goal.add_distance > goal.goal_distance:
					print("若是现在累计距离已经大于自己的目标距离，则根据超出的距离数生成新系数")
					beyond_distance = math.floor(goal.add_distance - goal.goal_distance)
					# if beyond_distance >= 15:
					# 	beyond_distance = 5
					RidingCoefficient.objects.update_freedom(user_id=user_id, beyond_distance=beyond_distance)
				else:
					pass
			print("即将创建打卡记录")
			record = self.create(
				goal_id=goal.goal_id,
				voucher_ref=voucher_ref,
				voucher_store=voucher_store,
				distance=distance,
				record_time=record_time,
				document=document
			)
			return record
		except Exception as e:
			logger.error(e)
			print(e)
			return None

	#
	# 获取时间
	def get_day_record(self, daydelta):
		"""
		:param day: 表示一个timedelta
		:return:
		"""
		# 判断现在的时间距离开始时间的时长
		# day = (timezone.now()-self.recod_time)
		# print(day)
		# 今天的日期加上
		today = timezone.now().date() + timedelta(daydelta)
		print(today, "这个时间加上一个时间段")
		# 明天
		end = today + timedelta(1)
		print(end, "today加上一天，表示的是那一天的一整天的时间段")
		return self.filter(record_time__range=(today, end))

	# 第一天是否存在打卡记录

	# user对某punch点赞
	def praise_punch(self, user_id, punch_id):
		try:
			praise = RidingPunchPraise(user_id=user_id, punch_id=punch_id)
			praise.save()
			record = self.get(punch_id=punch_id)
			record.praise += 1
			record.save()
		except Exception:
			pass

	# user对某punch举报
	def report_punch(self, user_id, punch_id):
		try:
			praise = RidingPunchReport(user_id=user_id, punch_id=punch_id)
			praise.save()
			record = self.get(punch_id=punch_id)
			record.report += 1
			record.save()
		except Exception:
			pass

	# 是否存在某user对某punch的点赞
	def exist_praise_punch(self, user_id, punch_id):
		record = RidingPunchPraise.objects.filter(user_id=user_id, punch_id=punch_id)
		if record:
			return True
		else:
			return False

	# 是否存在某user对某punch的点赞
	def exist_report_punch(self, user_id, punch_id):
		record = RidingPunchReport.objects.filter(user_id=user_id, punch_id=punch_id)
		if record:
			return True
		else:
			return False


class RidingPunchRecord(models.Model):
	""" Model for running task record
		To save user's actual running distance per day
	"""
	# 主键ID,标识打卡记录
	punch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	# 外键ID,标识对应目标
	goal = models.ForeignKey(RidingGoal, related_name="punch", on_delete=models.PROTECT)
	# Time when user creates the record
	record_time = models.DateTimeField(null=False)
	# 截图的引用地址
	# voucher_ref = models.CharField(max_length=256, null=False)
	voucher_ref = models.TextField(null=False)
	# 截图的存储地址
	voucher_store = models.CharField(max_length=512, null=False)
	# 跑步距离
	distance = models.FloatField(default=0)
	# 被赞数
	praise = models.IntegerField(default=0)
	# 被举报数
	report = models.IntegerField(default=0)
	# 保存的一段话
	document = models.TextField(default=" ", null=True)
	# 重新打卡
	reload = models.IntegerField(default=0, null=True)
	# 指定一个Manager
	objects = RidingPunchRecordManager()


class CommentManager(models.Manager):
	def praise_comment(self, user_id, punch_id):
		try:
			praise = RidingPunchPraise(user_id=user_id, punch_id=punch_id)
			praise.save()
			record = self.get(id=punch_id)
			record.prise += 1
			record.save()
		except Exception as e:
			print(e)

	# user对某punch举报

	def report_comment(self, user_id, punch_id):
		try:
			report = RidingPunchReport(user_id=user_id, punch_id=punch_id)
			report.save()
			record = self.get(id=punch_id)
			record.report += 1
			record.save()
		except Exception as e:
			print(e)


# 用户评论表
class CommentRiding(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4)
	user = models.ForeignKey(UserInfo, related_name="ridin")
	content = models.CharField(null=False, max_length=255)
	c_time = models.DateTimeField()
	prise = models.IntegerField(default=0)
	report = models.IntegerField(default=0)
	voucher_ref = models.TextField(null=True)
	# 截图的存储地址
	voucher_store = models.TextField()
	is_delete = models.BooleanField(default=0, auto_created=True)
	is_top = models.BooleanField(default=0)
	objects = CommentManager()

	@property
	def get_some_message(self):
		user = UserInfo.objects.filter(user_id=self.user_id)
		if user:
			user = user[0]
			return user

	class Meta:
		db_table = "on_riding_comments"


# 点赞
class RidingPunchPraise(models.Model):
	# 点赞的人
	user_id = models.IntegerField()
	# punch id
	punch_id = models.UUIDField()

	class Meta:
		unique_together = ("punch_id", "user_id")


# 举报
class RidingPunchReport(models.Model):
	# 举报的人
	user_id = models.IntegerField(null=False, default=0)
	# punch id
	punch_id = models.UUIDField(null=False, default=uuid.uuid4)

	class Meta:
		unique_together = ("punch_id", "user_id")


class Finish_SaveManager(models.Manager):
	def save_finish(self, goal_id):
		print("打印一下用户的id，看看是不是自己的", goal_id)
		goal = RidingGoal.objects.filter(goal_id=goal_id)
		print(goal, "看看是否查询到了值")
		if goal:
			goal = goal[0]
			finish_dict = {
				"goal_id": str(goal_id),
				"user_id": goal.user_id,
				"activity_type": goal.activity_type,
				"goal_type": goal.goal_type,
				"start_time": goal.start_time,
				"goal_day": goal.goal_day,
				"status": "已经结束",
				"mode": goal.mode,
				"guaranty": goal.guaranty,
				"down_payment": goal.down_payment,
				"coefficient": goal.coefficient,
				"bonus": goal.bonus,
				"none_punch_days": goal.none_punch_days,
				"goal_distance": goal.goal_distance,
				"kilos_day": goal.kilos_day,
				"left_distance": goal.left_distance,
				"reality_price": goal.reality_price,
				"deserve_price": goal.deserve_price,
				"down_num": goal.down_num,
				"activate_deposit": goal.activate_deposit,
				"average": goal.average,
				"add_distance": goal.add_distance,
				"extra_earn": goal.extra_earn,
				"punch_day": goal.punch_day,
				"settle_time": timezone.now().strftime("%Y-%m-%d")
			}
			try:
				self.create(**finish_dict)
				return True
			except Exception as e:
				print("创建记录失败", e)
		else:
			return False


ACTIVITY_CHOICES = (
	(u'0', u'作息'),
	(u'1', u'跑步'),
	(u'2', u'阅读(尝新)'),
	# (u'2', u'购书阅读2期')
	(u'3', u'步行'),
	(u'4', u'骑行'),
)

STATUS_CHOICES = (
	(u'ACTIVE', u'进行中'),
	(u'FAILED', u'失败'),
	(u'SUCCESS', u'成功'),
	(u'PENDING', u'等待支付')
)
GOAL_CHOICES = (
	(0, '自由模式'),
	(1, '日常模式')
)


class Riding_Finish_Save(models.Model):
	id = models.IntegerField(primary_key=True, auto_created=True)
	# 目标距离
	goal_distance = models.FloatField(null=True)
	# 单日目标距离，对于自由模式来说，kilos_day为单日目标上限
	kilos_day = models.FloatField(null=True)
	# 剩余距离, 只针对自由模式有效
	left_distance = models.FloatField(null=True)
	# 用户实际要付出的金额
	reality_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
	# 用户应该要付出的金额
	deserve_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
	# 扣完底金需要的次数
	down_num = models.IntegerField(default=1, null=False)
	# 平均每次要扣的
	average = models.DecimalField(max_digits=12, decimal_places=2, null=False)
	# 活动押金
	activate_deposit = models.DecimalField(max_digits=12, decimal_places=2, null=False)
	# 累计距离,只对自由模式有效
	add_distance = models.FloatField(default=0, null=True)
	# 活动额外收益
	extra_earn = models.DecimalField(max_digits=12, decimal_places=2, null=False)
	# 用户打卡的天数
	punch_day = models.IntegerField(null=False)
	goal_id = models.CharField(max_length=255, null=True)
	user_id = models.IntegerField(null=False)
	activity_type = models.CharField(null=False, max_length=16, choices=ACTIVITY_CHOICES, default="0")
	# 0为自由模式, 1为日常模式
	goal_type = models.IntegerField(null=False, default=1, choices=GOAL_CHOICES)
	# 开始时间
	start_time = models.DateTimeField(null=False)
	# 目标天数
	goal_day = models.IntegerField(null=False, default=0)
	# Task status, pending, active, paused, complete
	status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING')
	# User selected task mode, 普通, 学生, 尝试, etc
	MODE_CHOICES = (
		(u'N', u'尝新'),
		(u'O', u'普通'),
		(u'P', u'体验'),
		(u'U', u'升级'),
	)
	# 学生或普通模式的选择
	mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="N")
	# 保证金
	guaranty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	# 底金
	down_payment = models.DecimalField(max_digits=12, decimal_places=2)
	# 系数
	coefficient = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	# 瓜分金额
	bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)

	# 已经发生过的未完成天数, 用于计算下一次扣除底金与保证金的金额数
	none_punch_days = models.IntegerField(null=False, default=0)
	settle_time = models.DateTimeField()
	objects = Finish_SaveManager()

	class Meta:
		db_table = "on_riding_finish_save"


class RidingReply(models.Model):
	id = models.IntegerField(primary_key=True, auto_created=True)
	user_id = models.IntegerField()
	other_id = models.CharField(null=False, max_length=255)
	r_content = models.TextField(null=False)
	create_time = models.DateTimeField(null=True)

	@property
	def get_user_message(self):
		user = UserInfo.objects.filter(user_id=self.user_id)
		if user:
			user = user[0]
			return user

	class Meta:
		db_table = "on_ridingreply"


class RidingCoefficientManager(models.Manager):
	# todo
	# 自由模式更新系数，beyond_distance：比基础目标多余的距离
	def update_freedom(self, beyond_distance, user_id):
		"""每次自由模式打卡时候调用此函数，获取用户输入的距离，获取用户之前的累计距离"""
		try:
			user = self.filter(user_id=user_id)
			if user:
				user = user[0]
			default = user.default_coeff
			print('自由模式系数更新 \r\n user_id：{}  超出距离：{}'.format(user_id, beyond_distance))

			if beyond_distance < 3:
				user.new_coeff = default
			elif 3 <= beyond_distance < 6:
				user.new_coeff = default * decimal.Decimal(1.1)
			elif 6 <= beyond_distance < 9:
				user.new_coeff = default * decimal.Decimal(1.2)
			elif 9 <= beyond_distance < 12:
				user.new_coeff = default * decimal.Decimal(1.3)
			elif 12 <= beyond_distance < 14.99:
				user.new_coeff = default * decimal.Decimal(1.4)
			else:
				user.new_coeff = default * decimal.Decimal(1.5)

			user.save()
			return user.new_coeff
		except Exception as e:
			logger.error(e)
			print(e)

	# 更新日常模式的每日悉数加成
	def update_daily(self, user_id, beyond_distance, finish_week_day):
		print('日常模式系数更新', user_id, beyond_distance, finish_week_day)
		user = self.filter(user_id=user_id)

		try:
			if user:
				user = user[0]
			default = user.default_coeff
			print('默认系数', default)
			# 1. 超过基础目标：每3km，+10%（上限+50%，仅当天）
			# 2. 完成超过3次合格目标：每1次，+10%（上限40%，即一周完成7次合格目标）
			# 第一种情况，当周打卡天数小于等于三次
			if finish_week_day <= 3:
				# 当日超出目标距离如果小于3
				if beyond_distance < 3:
					# 当前new_coeff 设置为默认参数
					user.new_coeff = default
				# 当日超出目标距离如果大于等于3 且小于6
				elif 3 <= beyond_distance < 6:
					# 当前new_coeff 默认系数 + 10%
					user.new_coeff = default * decimal.Decimal(1.1)
				# 当日超出目标距离如果大于等于6 且小于9
				elif 6 <= beyond_distance < 9:
					# 当前new_coeff 默认系数 + 20%
					user.new_coeff = default * decimal.Decimal(1.2)
				# 当日超出目标距离如果大于等于9 且小于12
				elif 9 <= beyond_distance < 12:
					# 当前new_coeff 默认系数 + 30%
					user.new_coeff = default * decimal.Decimal(1.3)
				# 当日超出目标距离如果大于等于12 且小于14.99
				elif 12 <= beyond_distance < 14.99:
					# 当前new_coeff 默认系数 + 40%
					user.new_coeff = default * decimal.Decimal(1.4)
				else:
					# 当日超出目标距离如果大于等于15， 当前new_coeff 默认系数+50%
					user.new_coeff = default * decimal.Decimal(1.5)
				user.save()
				return user.new_coeff
			else:
				# 第二种情况，当周打卡完成天数超过3天
				# extra_day 此时一定大于0
				extra_day = finish_week_day - 3
				print('本周超额完成目标{}'.format(extra_day))
				# 如果完成超过天数大于4， 则extra_dya=4
				if extra_day > 4:
					extra_day = 4
				if beyond_distance < 3:
					user.new_coeff = default * decimal.Decimal("1.{}".format(int(extra_day)))
				elif 3 <= beyond_distance < 6:
					user.new_coeff = default * decimal.Decimal("1.{}".format(1 + int(extra_day)))
				elif 6 <= beyond_distance < 9:
					user.new_coeff = default * decimal.Decimal("1.{}".format(2 + int(extra_day)))
				elif 9 <= beyond_distance < 12:
					user.new_coeff = default * decimal.Decimal("1.{}".format(3 + int(extra_day)))
				elif 12 <= beyond_distance < 14.99:
					user.new_coeff = default * decimal.Decimal("1.{}".format(4 + int(extra_day)))
				else:
					user.new_coeff = default * decimal.Decimal("1.{}".format(5 + int(extra_day)))
				user.save()
				return user.new_coeff

		except Exception as e:
			logger.error(e)
			print(e)

	# 由于用户没有打卡，或者是用户打卡的距离不符合要求，此时用户的新系数等于默认系数
	def defaultTonew(self, user_id, goal_id):
		user = self.filter(user_id=user_id)
		try:
			if user:
				user = user[0]
				user.new_coeff = user.default_coeff
				user.save()
		except Exception as e:
			logger.error(e)


class RidingCoefficient(models.Model):
	# 用户id
	user_id = models.IntegerField(null=False, primary_key=True)
	# 用户的默认系数
	default_coeff = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=1)
	# 当用户打卡之后生成的新系数
	new_coeff = models.FloatField(null=False, default=0)
	SLEEP_TYPE = (
		(0, "自由"),
		(1, '日常')
	)
	goal_type = models.SmallIntegerField(null=False, choices=SLEEP_TYPE, default=0)
	objects = RidingCoefficientManager()

	class Meta:
		db_table = "on_ridingcoefficient"
