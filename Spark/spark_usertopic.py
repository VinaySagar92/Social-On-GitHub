# importing SparkContext and SQLContext from pyspark for batch processing
from pyspark.sql import SparkSession
from pyspark import SparkContext
from pyspark.sql import SQLContext
from pyspark.sql import Row
from pyspark.sql.functions import explode
import random
from cassandra.cluster import Cluster
import os
import pyspark_cassandra
import pyspark
from datetime import datetime

# Creating a Cluster object to connect to Cassandra cluster and keyspace
cluster = Cluster(['54.218.131.115', '54.245.65.143', '54.203.126.6', '52.26.161.169'])

# Creating SparkSession, Spark Context and SQL Context Objects
spark = SparkSession.builder \
            .appName("S3 READ TEST") \
            .config("spark.executor.cores", "6") \
            .config("spark.executor.memory", "6gb") \
	    .config("spark.sql.join.preferSortMergeJoin", "false") \
	    .getOrCreate()

sc=spark.sparkContext
sqlContext = SQLContext(sc)

# Configuring hadoop and spark context with aws key id and secret access secret key to run Spark job and read from S3
hadoop_conf=sc._jsc.hadoopConfiguration()
hadoop_conf.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
hadoop_conf.set("fs.s3a.awsAccessKeyId", os.environ['AWS_ACCESS_KEY_ID'])
hadoop_conf.set("fs.s3a.awsSecretAccessKey", os.environ['AWS_SECRET_ACCESS_KEY'])

#df11 = spark.read.json("s3a://vinaysagar-bucket/2017/2017-*.json.gz")
#df11 = spark.read.json("s3a://vinaysagar-bucket/2018/2018-jan-*.json.gz")

# filtering rows with just the three relevant events
sqlContext.registerDataFrameAsTable(df11, "df11_event_table")

# creating new dataframes with just the relevant columns
df11_altered_union = sqlContext.sql("SELECT actor, repo, created_at FROM df11_event_table WHERE type = 'ForkEvent' or type = 'CommitCommentEvent' and actor is NOT NULL and created_at IS NOT NULL and repo IS NOT NULL") \
			.na.drop(subset=('created_at')).persist(pyspark.StorageLevel.MEMORY_ONLY)

sqlContext.registerDataFrameAsTable(df11_altered_union, "df11_altered_union_table")


def splitRepo(a):
	b = datetime.strptime(a.created_at.split(" ")[0], '%Y-%m-%d')
	return ((a.actor.login, b), a.repo.name)

def splitTopic(a):
	b = datetime.strptime(a.time.split(" ")[0], '%Y-%m-%d')
	return ((a.user, b), a.topic)

def splitUser(a):
	b = datetime.strptime(a.time.split(" ")[0], '%Y-%m-%d')
	return ((a.topic, b), a.user)

def comb(a):
	return [a]

def merg(a, b):
	a.append(b)
	return a

def mergComb(a, b):
	a.extend(b)
	return a

# getting all the user to repo one-to-one mappings
user_repo_map11 = df11_altered_union.rdd.map(lambda x: {"user": x.actor.login, "time": x.created_at, "repo": x.repo.name}).toDF()
user_repo_mapN = user_repo_map11.na.drop(subset=('user', 'time')).rdd.map(lambda c: {"repo": c[0], "time": c[1], "user": c[2]}).toDF().persist(pyspark.StorageLevel.MEMORY_ONLY)

#print(user_repo_mapN.show())

### Repo to Topic to be used for user to topic mapping
#Topics that are available are given as a list
top = ['3D', 'Ajax', 'Algorithm', 'Amp', 'Android', 'Angular', 'Ansible', 'API', 'Adruino', 'ASP.NET', 'Atom', 'Awesome Lists', 'Amazon Web Services', 'Azure', 'Babel', 'Blockchain', 'Bootstrap', 'Bot', 'C', 'Chrome', 'Chrome extension', 'Command line interface', 'Clojure', 'Code quality', 'Code review', 'Compiler', 'Coninuous integration', 'C++', 'Cryptocurrency', 'Crystal', 'C#', 'CSS', 'Data structures', 'Data visualization', 'Database', 'Deep leaning', 'Dependency management', 'Deployment', 'Django', 'Docker', 'Documentation', '.NET', 'Electron', 'Elixir', 'Emacs', 'Ember', 'Emoji', 'Emulator', 'ES6', 'ESLint', 'Ethereum', 'Express', 'Firebase', 'Firefox', 'Flask', 'Font', 'Framework', 'Front end', 'Game engine', 'Git', 'GitHub API', 'Go', 'Google', 'Gradle', 'GraphQL', 'Gulp', 'Haskell', 'Homebrew', 'Homebridge', 'HTML', 'HTTP', 'Icon font', 'iOS', 'IPFS', 'Java', 'Javascript', 'Jekyll', 'jQuery', 'JSON', 'The Julia Language', 'Jupyter Notebook', 'Koa', 'Kotlin', 'Kubernetes', 'Laravel', 'LaTex', 'Library', 'Linux', 'Localization', 'Lua', 'Machine learning', 'macOS', 'Markdown', 'Mastodon', 'Material design', 'MATLAB', 'Maven', 'Minecraft', 'Mobile', 'Monero', 'MongoDB', 'Mongoose', 'Monitoring', 'MvvmCross', 'MySQL', 'NativeScript', 'Nim', 'Natural language processing', 'Node.js', 'NoSQL', 'npm', 'Objective-C', 'OpenGL', 'Operating System', 'P2P', 'Package manager', 'Language parsing', 'Perl', 'Perl 6', 'Phaser', 'PHP', 'Pixel Art', 'PostgreSQL', 'Project management', 'Publishing', 'PWA', 'Python', 'Qt', 'R', 'Rails', 'Raspberry Pi', 'Ratchet', 'React', 'React Native', 'ReactiveUI', 'Redux', 'REST API', 'Ruby', 'Rust', 'Sass', 'Scala', 'scikit-learn', 'Software-defined networking', 'Security', 'Server', 'Serverless', 'Shell', 'Sketch', 'SpaceVim', 'Spring Boot', 'SQL', 'Storybook', 'Support', 'Swift', 'Symfony', 'Telegram', 'Tensorflow', 'Terminal', 'Terraform', 'Twitter', 'Typescript', 'Ubuntu', 'Unity', 'Unreal Engine', 'Vagrant', 'Vim', 'Virtual Reality', 'Vue.js', 'Wagtail', 'Web Components', 'Web App', 'Webpack', 'Windows', 'Wodplate', 'Wordpress', 'Xamarin', 'XML']
# Creating a RDD by mapping repos with topics from the list of topics
df11_altered = sqlContext.sql("SELECT repo FROM df11_altered_union_table WHERE repo IS NOT NULL")

def ran(a):
        b = random.choice(top)
        return (a.repo.name, b)

def comb_topic(a):
        return a

def merg_topic(a, b):
	return a

repo_topic = df11_altered.rdd.map(lambda c: {"repo": c.repo.name, "topic": random.choice(top)}).toDF().persist(pyspark.StorageLevel.MEMORY_ONLY)



# Performing an inner join for the user to topic relation on the two dataframes created
df_join = user_repo_mapN.join(repo_topic, user_repo_mapN.repo == repo_topic.repo).select("user", "time", "topic").persist(pyspark.StorageLevel.MEMORY_ONLY)
df_join.explain(True)

df_join_re = df_join.repartition("user")

### User to Topic Mapping
# grouping all records for a given username to get all topics that the user is following and has contributed to
user_topic_map = df_join_re.rdd.map(splitTopic).combineByKey(comb, merg, mergComb).map(lambda c: ((c[0][0], c[0][1], c[1])))
user_topic_db = user_topic_map.toDF().na.drop(subset=('_1', '_2')).rdd.map(lambda c: (c[0], c[1], c[2]))
# writing to cassandra table usertopic
print(user_topic_db.toDF().show())
print(user_topic_db.toDF().dtypes)
user_topic_db.saveToCassandra("events", "usertopic")
