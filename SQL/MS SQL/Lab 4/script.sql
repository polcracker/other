declare @test datetime = '21.03.2016';
declare @curDateTime datetime = GETDATE();
declare @curDate date = GETDATE();

select
	@test as 'Test Datetime', 
	@curDateTime as 'Curdate in datetime',  
	@curDate as 'Curdate in date', 
	cast((GETDATE() - 1) as date) as 'Yesterday [CAST]';

/* �) ������ ���������, �������� ����������� �����; */

select 
	Pat_Name, 
	Pat_Surname, 
	Pat_Middle_name
from
	Patient, Specialty, Doctor_Specialty, Reception_History 
where 
	Doctor_Specialty.id_doc_spec = Reception_History.id_doc_spec and
	Specialty.id_spec = Doctor_Specialty.id_spec and
	Patient.id_pat = Reception_History.id_pat and
	Spec_Name = '��������' and
	cast(Date_reception as date) = cast((GETDATE() - 1) as date)

/* �) ������, ����������� ��������� �������������; */

select distinct
	Doctor.Doc_Name, 
	Doctor.Doc_Surname, 
	Doctor.Doc_Middle_name 
from
	Doctor, Doctor_Specialty, Specialty, Doctor_Specialty as Doctor_Specialty_1
where 
	Doctor_Specialty.id_spec = Specialty.id_spec and
	Doctor.id_doc = Doctor_Specialty.id_doc and
	Doctor.id_doc = Doctor_Specialty_1.id_doc and
	Doctor_Specialty_1.id_spec <> Doctor_Specialty.id_spec

/* �) ���������, ���������� � �������, � ����������; */

select distinct
	Patient.id_pat, 
	Patient.Pat_Name, 
	Patient.Pat_Surname, 
	Patient.Pat_Middle_name
from
	Specialty as Specialty_1,
	Doctor_Specialty as Doctor_Specialty_1,
	Reception_History as Reception_History_1,
	Patient,
	Reception_History,
	Doctor_Specialty,
	Specialty
where
	Doctor_Specialty.id_spec = Specialty.id_spec and
	Reception_History.id_doc_spec = Doctor_Specialty.id_doc_spec and
	Patient.id_pat = Reception_History.id_pat and

	Reception_History_1.id_pat = Reception_History.id_pat and
	Doctor_Specialty_1.id_doc_spec = Reception_History_1.id_doc_spec and
	Specialty_1.id_spec = Doctor_Specialty_1.id_spec and

	Specialty.Spec_Name = '������' and 
	[Specialty_1].Spec_Name = '���������'

/* *) ������ ���������, ��� ��� �� �������� ��������� � �������� ����� �� */
select * from Patient
where
	Pat_Name not like '%[��]%'
go

/* *) ������ ���������, ��� ��� ���������� �� "A" */

select * from Patient
where
	Pat_Name like '�%'
go

/* *) ������ ������, ��� ������� ���������� �� "A" ��� "�", �� � �������� ������ ����� �� ��������� "�" */

select * from Doctor
where
	Doc_Surname like '[��][^�]%'
go

/* *) ������ ���������, � ������� �� ������ �������� */

select * from Patient
where
	Pat_Middle_name is null
go

/* *) ������ ������, ��� ���� �������� ��������� ����� 1969-01-01 � 1986-01-01 */
select * from Doctor
where
	Doc_Bday_date between '1969-01-01' and '1986-01-01'
go

/* *) ������ ���������� ���������������� ��������� � ���� �����������, id �������� ����������� ��������� { 3, 1, 4 } */
select id_pat, Date_reception from Reception_History
where
	id_pat in (3, 1, 4)
go