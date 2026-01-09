import React, { useState, useMemo, useEffect } from 'react';
import { useReactTable, getCoreRowModel, flexRender } from '@tanstack/react-table';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { SketchPicker } from "@hello-pangea/color-picker";
import { BrowserRouter, Routes, Route, useNavigate, Navigate } from 'react-router-dom';
import './Horario.css';
import axios from 'axios';
import Select from 'react-select';
import Button from '@mui/material/Button';
import EditIcon from '@mui/icons-material/Edit';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faFilePdf, faFileExcel } from '@fortawesome/free-solid-svg-icons'
import { FaPalette } from "react-icons/fa";
import { FaSearch } from "react-icons/fa";

const days = ['1', '2', '3','4', '5', '6','7', '8', '9','10', '11', '12','13', '14', '15', '16', '17', '18','19', '20', '21', '22','24', '25', '26', '27','28', '29','30'];
const mes = ['Enero', 'Febrero','Marzo','Abril', 'Mayo','Junio','Julio', 'Agosto','Septiembre','Octubre', 'Noviembre','Diciembre'];
const anio = ['2025', '2026'];



const monthNameToNumber = {
  "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
  "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
  "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
};

function getMonthNumber(monthName) {
  return monthNameToNumber[monthName];
}

function Horario() {

  const [form, setForm] = useState({ 
    id:'',
    mes: '', 
    anio: '',
    razon_social: '',
    nombre_comercial: '',
    direccion: '',
    nombre_instalacion: '',
    ciudad: '',
    provincia: '',
    codigo: '',
    nombre_puesto: '',
    nombre: '',
    apellido: '',
    cedula: '',
    hora_ingreso: '',
    fecha_inicio: '',
    fecha_fin: '',
    hora_salida: '',
    tipo: '',
    rotativo:'',
    estado:'',
    tipo:''
  });
  const [selectedColor, setSelectedColor] = useState("#ffffffff");
  const [cellColors, setCellColors] = useState({});
  const [showPicker, setShowPicker] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showModalEdit, setShowModalEdit] = useState(false);
  const [clientes, setClientes] = useState([]); // Lista de razones sociales
  const [instalaciones, setInstalaciones] = useState([]);
  const [personas, setPersonas] = useState([]);
  const [fecha, setFecha] = useState('');
  const [puestos, setPuestos] = useState([]);
  const [horarios, setHorarios] = useState([]);
  const rotativos = ['3-3-1', '3-3-2','2-2-2','6-2', '5-2','6-1','2-2-1','1-2-4','2-1-7','3-2-2','4-2-2','2-4-2'];
  const estados = ['ACTIVO', 'INACTIVO'];
  const [newRecord, setNewRecord] = useState({
  nombre: '',
  apellido: '',
  cedula: '',
  tipo: ''
  });
  const [data, setData] = useState([]);

  const handleEditClick = (item) => {
    console.log(item)
    console.log(form)
  setForm({
    fecha_inicio: item.fecha_inicio || '',
    fecha_fin: item.fecha_fin || '',
    persona: personas.find(p => `${p.apellidos} ${p.nombres}` === `${item.apellidos} ${item.nombres}`)?.id || '',
    cliente: clientes.find(c => c.razon_social === item.razonSocial)?.id || '',
    instalacion: instalaciones.find(i => i.nombre === item.nombreinstalacion)?.id || '',
    puesto: puestos.find(p => p.nombre === item.nombrePuesto)?.id || '',
    horario: horarios.find(h => h.denominativo === item.denominativo)?.id || '',
    rotativo: item.rotativo,
    estado:item.estado,
    id:item.idAsignacion,
    // Estos campos los puedes llenar si los tienes en el item
    mes: form.mes,
    anio: form.anio,
    razon_social: '',
    nombre_comercial: '',
    direccion: '',
    nombre_instalacion: '',
    ciudad: '',
    provincia: '',
    codigo: '',
    nombre_puesto: '',
    nombre: '',
    apellido: '',
    cedula: item.cedula || '',
    hora_ingreso: item.hingreso || '',
    hora_salida: item.hsalida || '',
    tipo: '',
  });

  setShowModalEdit(true); // Abre el modal de edición
};

  const BuscarAsignaciones = async () => {
    const monthNumber = getMonthNumber(form.mes);
    if (!form.mes || !form.anio) return;
    axios.get(`http://localhost:8000/api/asignaciones/${monthNumber}/${form.anio}/`)
      .then((response) => {
        console.log(response)
        const mappedData = response.data.map((item, index) => ({
          id: item.idAsignacion.toString(),
          name: `${item.apellidos || ''} ${item.nombres || ''}`,
          schedule: item ? Object.fromEntries(
            Array.from({ length: 31 }, (_, i) => {
              const day = `dia_${i + 1}`;
              return [String(i + 1), item[day]];
            })
          ) : {},
          cedula: item.cedula,
          orden: item.idAsignacion,
          cliente: item.razonSocial || '-',
          puestonombre: item.nombrePuesto || '-',
          puestohorario: item.denominativo || '-',
          hingreso: item.horaingreso || '-',
          hsalida: item.horasalida || '-',
          persona: item.apellidos + " " + item.nombres || '-',
          instalacion: item.codigo || '-',
          rotativo: item.rotativo,
          accion:<Button onClick={() => handleEditClick(item)} style={{ minWidth: 0, padding: 2 }}> <EditIcon style={{ color: '#f44336' }} /> </Button>

        }));
        setData(mappedData);
      })
      .catch((error) => {
        console.error('Error al obtener asignaciones:', error);
      });
  };




const DiasConSemana = ({ anio, mes }) => {
  const dias = useMemo(() => {
    if (!anio || !mes) return [];

    const ultimoDia = new Date(anio, mes, 0).getDate();
    const nombresDias = ["D", "L", "M", "X", "J", "V", "S"];

    return Array.from({ length: ultimoDia }, (_, i) => {
      const fecha = new Date(anio, mes - 1, i + 1);
      const diaSemana = nombresDias[fecha.getDay()];
      return { numero: i + 1, letra: diaSemana };
    });
  }, [anio, mes]);

  // 👇 Ahora sí, devolvemos el JSX
  return (
    <div style={{ display: "flex", justifyContent: "center", gap: "4px" }}>
      {dias.map((d) => (
        <div key={d.numero} style={{ textAlign: "center", width: "35px" }}>
          <div style={{ fontWeight: "bold" }}>{d.letra}</div>
          <div>{d.numero}</div>
        </div>
      ))}
    </div>
  );
};


  const handleNewRecordChange = (e) => {
  const { name, value } = e.target;
  setNewRecord({ ...newRecord, [name]: value });
};

const QuitarModalActualizartablaActualizarFormulario = () => {
  //setData([...data, newRecord]);
  setForm({
    mes: '',
    anio: '',
    razon_social: '',
    nombre_comercial: '',
    direccion: '',
    nombre_instalacion: '',
    ciudad: '',
    provincia: '',
    codigo: '',
    nombre_puesto: '',
    nombre: '',
    apellido: '',
    cedula: '',
    hora_ingreso: '',
    fecha_inicio: '',
    fecha_fin: '',
    hora_salida: '',
    tipo: '',
    cliente: '',
    persona: '',
    horario: '',
    puesto: '',
    rotativo: '',
    instalacion: ''
  });
  setShowModal(false);

  //setNewRecord({ nombre: '', apellido: '', cedula: '', tipo: '' }); // reset
};

const QuitarModalEditActualizartablaActualizarFormulario = () => {
  //setData([...data, newRecord]);
  setForm({
    mes: '',
    anio: '',
    razon_social: '',
    nombre_comercial: '',
    direccion: '',
    nombre_instalacion: '',
    ciudad: '',
    provincia: '',
    codigo: '',
    nombre_puesto: '',
    nombre: '',
    apellido: '',
    cedula: '',
    hora_ingreso: '',
    fecha_inicio: '',
    fecha_fin: '',
    hora_salida: '',
    tipo: '',
    cliente: '',
    persona: '',
    horario: '',
    puesto: '',
    rotativo: '',
    instalacion: ''
  });
  setShowModalEdit(false);

  //setNewRecord({ nombre: '', apellido: '', cedula: '', tipo: '' }); // reset
};

  const columns = useMemo(() => [
    {
      header: '',
      accessorKey: 'accion',
      cell: (info) => info.getValue(),
    },
    {
      header: 'H. INGRESO',
      accessorKey: 'hingreso',
      cell: (info) => info.getValue(),
    },
    {
      header: 'H. SALIDA',
      accessorKey: 'hsalida',
      cell: (info) => info.getValue(),
    },
    {
      header: '',
      accessorKey: 'instalacion',
      cell: (info) => info.getValue(),
    },
    {
      header: 'CLIENTE',
      accessorKey: 'cliente',
      cell: (info) => info.getValue(),
    },
    {
      header: 'PUESTO NOMBRE',
      accessorKey: 'puestonombre',
      cell: (info) => info.getValue(),
    },
    {
      header: 'H. PUESTO',
      accessorKey: 'puestohorario',
      cell: (info) => info.getValue(),
    },
    {
      header: 'H. GUARDIA',
      accessorKey: 'rotativo',
      cell: (info) => info.getValue(),
    },
    {
      header: '#',
      accessorKey: 'orden',
      cell: (info) => info.getValue(),
    },
    {
      header: 'CEDULA',
      accessorKey: 'cedula',
      cell: (info) => info.getValue(),
    },
    {
      header: 'APELLIDOS Y NOMBRES',
      accessorKey: 'persona',
      cell: (info) => info.getValue(),
    },
    ...days.map((day) => ({
      header: day,
      accessorKey: `schedule.${day}`,
      cell: ({ row }) => {
        const empleado = row.original;
        const turno = empleado.schedule[day] || '';
        const cellId = `${empleado.id}-${day}`;
        return (
          <div
            onClick={() => {
              setCellColors((prev) => ({
                ...prev,
                [cellId]: selectedColor
              }));
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
              padding: '4px',
              background: cellColors[cellId] || "#ffffffff",
              border: `2px solid ${cellColors[cellId] || "#d1eaff"}`,
              borderRadius: '4px',
              fontWeight: 'bold',
              cursor: "pointer",
            }}
          >
            {turno}
          </div>
        );
      },
    })),
  ], [data, selectedColor, cellColors]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  // 👉 Nuevo: mover filas
  const handleRowDragEnd = (result) => {
    if (!result.destination) return;
    const newData = Array.from(data);
    const [movedRow] = newData.splice(result.source.index, 1);
    newData.splice(result.destination.index, 0, movedRow);
    setData(newData);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

    const Asignar = async () => {
    console.log(form.rotativo)
    
    console.log(form.puesto)
    await fetch('http://localhost:8000/api/asignar-servicio/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        fecha_inicio: form.fecha_inicio,
        fecha_fin: form.fecha_fin,
        cliente_id: form.cliente,
        horario_id: form.horario,
        instalacion_id: form.instalacion,
        persona_id: form.persona,
        puesto_id: form.puesto,
        rotativo: form.rotativo,
        mes: form.fecha_inicio.split("-")[1],
        anio: form.fecha_inicio.split("-")[0],
        estado:form.estado,
        tipo: form.tipo,
      })
  })
  .then(res => res.json())
  .then(data => {
    console.log(data.message);
  })
  .catch(err => {
    console.log("error al guardar");
  });
  };


  const guardarEdicionAsignacion = async () => {
    console.log(form.rotativo)
    console.log(form.puesto)
    console.log(form.id)
    await fetch(`http://localhost:8000/api/editar-servicio/${form.id}/`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        fecha_inicio: form.fecha_inicio,
        fecha_fin: form.fecha_fin,
        cliente_id: form.cliente,
        horario_id: form.horario,
        instalacion_id: form.instalacion,
        persona_id: form.persona,
        puesto_id: form.puesto,
        rotativo: form.rotativo,
        mes: form.fecha_inicio.split("-")[1],
        anio: form.fecha_inicio.split("-")[0],
        estado:form.estado,
        tipo:form.tipo,
      })
  })
  .then(res => res.json())
  .then(data => {
    console.log(data.message);
  })
  .catch(err => {
    console.log("error al guardar");
  });
  };

  
    useEffect(() => {
      const fetchClientes = async () => {
        try {
          const res = await fetch('http://localhost:8000/api/clientes/');
          const data = await res.json();
          setClientes(data);
        } catch (error) {
          console.error('Error al cargar clientes:', error);
        }
      };
  
      fetchClientes();
    }, []); 
  
  
      useEffect(() => {
      const fetchInstalaciones = async () => {
        try {
          const res = await fetch('http://localhost:8000/api/instalaciones/');
          const data = await res.json();
          setInstalaciones(data);
        } catch (error) {
          console.error('Error al cargar instalaciones:', error);
        }
      };
  
      fetchInstalaciones();
    }, []); 
  
      
      useEffect(() => {
      const fetchPuestos = async () => {
        try {
          const res = await fetch('http://localhost:8000/api/puestos/');
          const data = await res.json();
          setPuestos(data);
        } catch (error) {
          console.error('Error al cargar puestos:', error);
        }
      };
  
      fetchPuestos();
    }, []);
  
  
      useEffect(() => {
      const fetchHorarios = async () => {
        try {
          const res = await fetch('http://localhost:8000/api/horarios/');
          const data = await res.json();
          console.log('Horarios cargados:', data);
          setHorarios(data);
        } catch (error) {
          console.error('Error al cargar horarios:', error);
        }
      };
  
      fetchHorarios();
    }, []);
  
      useEffect(() => {
        const fetchPersonas = async () => {
          try {
            const res = await fetch('http://localhost:8000/api/personas/');
            const data = await res.json();
            setPersonas(data);
          } catch (error) {
            console.error('Error al cargar personas:', error);
          }
        };
    
        fetchPersonas();
      },[]);










  

  const pdf = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/generar-pdf/', {
      headers: { Accept: 'application/pdf' },
    });
    if (!response.ok) throw new Error('Error al descargar PDF');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'horario.pdf');
    document.body.appendChild(link);
    link.click();
    link.remove();
  } catch (error) {
    console.error('Error al descargar PDF:', error);
  }
};


  const excel = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/generar-excel/', {
      headers: { Accept: 'application/excel' },
    });
    if (!response.ok) throw new Error('Error al descargar excel');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'horario.xlsx');
    document.body.appendChild(link);
    link.click();
    link.remove();
  } catch (error) {
    console.error('Error al descargar excel:', error);
  }
};

const guardarOrdenAsignacion = async (nuevoOrdenIds) => {
  try {
    const response = await fetch('http://localhost:8000/api/guardar-orden/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ orden: nuevoOrdenIds }),
    });
    console.log(response);
    const data = await response.json();

    if (response.ok) {
      console.log('Orden guardado exitosamente:', data);
    } else {
      console.error('Error al guardar orden:', data.message);
    }
  } catch (error) {
    console.error('Error en la solicitud:', error);
  }
};

const onDragEnd = (result) => {
  if (!result.destination) return;

  const items = Array.from(data); // filas es tu array de objetos asignación
  const [reordenado] = items.splice(result.source.index, 1);
  items.splice(result.destination.index, 0, reordenado);

  // Extraer solo los IDs en el nuevo orden
  const nuevoOrdenIds = items.map(item => item.id);

  // Guardar nuevo orden
  guardarOrdenAsignacion(nuevoOrdenIds);

  // Actualizar estado en el frontend (opcional)
  setData(items);
};








  return (
      
 
    <div className="horario-container">

      {showModal && (
      <div style={{
        position: 'fixed',
        top: 0, left: 0,
        width: '100%', height: '100%',
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex', justifyContent: 'center', alignItems: 'center',
        zIndex: 1000
      }}>
      <div >

      <div className="form-wrapper">
        <form className="grid-form">
          <div className="form-column">
          <label htmlFor="fecha">Fecha Inicio:</label>
          <input
            type="date"
            id="fecha_inicio"
            name="fecha_inicio"
            value={form.fecha_inicio}
            onChange={handleChange}
          />

          <label htmlFor="fecha">Fecha Fin:</label>
          <input
            type="date"
            id="fecha_fin"
            name="fecha_fin"
            value={form.fecha_fin}
            onChange={handleChange}/>
            <label>ESTADO:
<Select
    options={estados.map(h => ({
      value: h,
       label: h 
    }))}
    onChange={selected =>
      setForm(prev => ({
        ...prev,
        estado: selected?.value || ''
      }))
    }
    value={estados.map(h => ({
        value: h,
       label: h 
      }))
      .find(opt => opt.value === form.estado)}
    placeholder="Seleccione estado"
    menuPortalTarget={document.body}
  styles={{
    menuPortal: base => ({ ...base, zIndex: 9999 }),
    menu: base => ({ ...base, zIndex: 9999 })
  }}
  />
</label>
          </div>
  {/* PERSONA */}
  <div className="form-column">
    <h3>PERSONA</h3>
    <Select

      options={personas.map(p => ({ value: p.id, label:`${p.nombres} ${p.apellidos} (${p.tipo})` }))}
      onChange={selected => setForm(prev => ({ ...prev, persona: selected?.value || '' }))}
      value={personas
        .map(p => ({ value: p.id, label: `${p.nombres} ${p.apellidos} (${p.tipo})` }))
        .find(opt => opt.value === form.persona)}
      placeholder="Seleccione una persona"
    />
  </div>

  {/* CLIENTE */}
  <div className="form-column">
    <h3>CLIENTE</h3>
    <Select
      options={clientes.map(c => ({ value: c.id, label: c.razon_social }))}
      onChange={selected => setForm(prev => ({ ...prev, cliente: selected?.value || '' }))}
      value={clientes
        .map(c => ({ value: c.id, label: c.razon_social }))
        .find(opt => opt.value === form.cliente)}
      placeholder="Seleccione un cliente"
    />
  </div>

  {/* INSTALACIÓN */}
  <div className="form-column">
    <h3>INSTALACIÓN</h3>
    <Select
      options={instalaciones.map(i => ({ value: i.id, label: i.nombre }))}
      onChange={selected => setForm(prev => ({ ...prev, instalacion: selected?.value || '' }))}
      value={instalaciones
        .map(i => ({ value: i.id, label: i.nombre }))
        .find(opt => opt.value === form.instalacion)}
      placeholder="Seleccione una instalación"
    />
  </div>

  {/* PUESTO */}
  <div className="form-column">
    <h3>PUESTO</h3>
    <Select
      options={puestos.map(p => ({ value: p.id, label: p.nombre }))}
      onChange={selected => setForm(prev => ({ ...prev, puesto: selected?.value || '' }))}
      value={puestos
        .map(p => ({ value: p.id, label: p.nombre }))
        .find(opt => opt.value === form.puesto)}
      placeholder="Seleccione un puesto"
    />
  </div>

  {/* HORARIO */}
  <div className="form-column">
    <h3>HORARIO</h3>

<label>DÍAS:
  <Select
    options={horarios.map(h => ({
      value: h.id,
      label: h.denominativo
    }))}
    onChange={selected =>
      setForm(prev => ({
        ...prev,
        horario: selected?.value || ''
      }))
    }
    value={horarios
      .map(h => ({
        value: h.id,
        label: h.denominativo 
      }))
      .find(opt => opt.value === form.horario)}
    placeholder="Seleccione horario"
    menuPortalTarget={document.body}
  styles={{
    menuPortal: base => ({ ...base, zIndex: 9999 }),
    menu: base => ({ ...base, zIndex: 9999 })
  }}
  />
    
</label>
<label>HORARIO ROTATIVO:
<Select
    options={rotativos.map(h => ({
      value: h,
       label: h 
    }))}
    onChange={selected =>
      setForm(prev => ({
        ...prev,
        rotativo: selected?.value || ''
      }))
    }
    value={rotativos.map(h => ({
        value: h,
       label: h 
      }))
      .find(opt => opt.value === form.rotativo)}
    placeholder="Seleccione horario"
    menuPortalTarget={document.body}
  styles={{
    menuPortal: base => ({ ...base, zIndex: 9999 }),
    menu: base => ({ ...base, zIndex: 9999 })
  }}
  />
</label>

  </div>

  <button type="button" className="btn"   
  onClick={async() => {
      try {
      await Asignar(); // Espera a que el POST termine
      await BuscarAsignaciones(); // Luego actualiza la tabla
      QuitarModalActualizartablaActualizarFormulario(); // Cierra el modal
    } catch (err) {
      console.error("Error durante la asignación");
    }
   
  }}>Asignar</button>   
  
  {/*<button type="button" className="btn" onClick={handleSaveNewRecord}>Guardar</button>*/}
  <button type="button" className="btn" 

  
  
  
  
  onClick={() => {setShowModal(false);
    setForm({
    mes: '',
    anio: '',
    razon_social: '',
    nombre_comercial: '',
    direccion: '',
    nombre_instalacion: '',
    ciudad: '',
    provincia: '',
    codigo: '',
    nombre_puesto: '',
    nombre: '',
    apellido: '',
    cedula: '',
    hora_ingreso: '',
    fecha_inicio: '',
    fecha_fin: '',
    hora_salida: '',
    tipo: '',
    cliente: '',
    persona: '',
    horario: '',
    puesto: '',
    rotativo: '',
    instalacion: '',
    estado:''
  });

  }
  }
    
    
    
    >
    Cancelar
    </button>
</form>
  </div>


    </div>
  </div>

)}

      {showModalEdit && (
      <div style={{
        position: 'fixed',
        top: 0, left: 0,
        width: '100%', height: '100%',
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex', justifyContent: 'center', alignItems: 'center',
        zIndex: 1000
      }}>
      <div >

      <div className="form-wrapper">
        <form className="grid-form">
          <div className="form-column">
          <label htmlFor="fecha">Fecha Inicio:</label>
          <input
            type="date"
            id="fecha_inicio"
            name="fecha_inicio"
            value={form.fecha_inicio}
            onChange={handleChange}
          />

          <label htmlFor="fecha">Fecha Fin:</label>
          <input
            type="date"
            id="fecha_fin"
            name="fecha_fin"
            value={form.fecha_fin}
            onChange={handleChange}/>
          <label>ESTADO:
          <Select
              options={estados.map(h => ({
                value: h,
                label: h 
              }))}
              onChange={selected =>
                setForm(prev => ({
                  ...prev,
                  estado: selected?.value || ''
                }))
              }
              value={estados.map(h => ({
                  value: h,
                label: h 
                }))
                .find(opt => opt.value === form.estado)}
              placeholder="Seleccione estado"
              menuPortalTarget={document.body}
            styles={{
              menuPortal: base => ({ ...base, zIndex: 9999 }),
              menu: base => ({ ...base, zIndex: 9999 })
            }}
            />
          </label>
          </div>
  {/* PERSONA */}
  <div className="form-column">
    <h3>PERSONA</h3>
    <Select
      options={personas.map(p => ({ value: p.id, label:`${p.nombres} ${p.apellidos} (${p.tipo})` }))}
      onChange={selected => setForm(prev => ({ ...prev, persona: selected?.value || '' }))}
      value={personas
        
        .map(p => ({ value: p.id, label: `${p.nombres} ${p.apellidos}` }))
        .find(opt => opt.value === form.persona)}
      placeholder="Seleccione una persona"
    />
  </div>

  {/* CLIENTE */}
  <div className="form-column">
    <h3>CLIENTE</h3>
    <Select
      options={clientes.map(c => ({ value: c.id, label: c.razon_social }))}
      onChange={selected => setForm(prev => ({ ...prev, cliente: selected?.value || '' }))}
      value={clientes
        .map(c => ({ value: c.id, label: c.razon_social }))
        .find(opt => opt.value === form.cliente)}
      placeholder="Seleccione un cliente"
    />
  </div>

  {/* INSTALACIÓN */}
  <div className="form-column">
    <h3>INSTALACIÓN</h3>
    <Select
      options={instalaciones.map(i => ({ value: i.id, label: i.nombre }))}
      onChange={selected => setForm(prev => ({ ...prev, instalacion: selected?.value || '' }))}
      value={instalaciones
        .map(i => ({ value: i.id, label: i.nombre }))
        .find(opt => opt.value === form.instalacion)}
      placeholder="Seleccione una instalación"
    />
  </div>

  {/* PUESTO */}
  <div className="form-column">
    <h3>PUESTO</h3>
    <Select
      options={puestos.map(p => ({ value: p.id, label: p.nombre }))}
      onChange={selected => setForm(prev => ({ ...prev, puesto: selected?.value || '' }))}
      value={puestos
        .map(p => ({ value: p.id, label: p.nombre }))
        .find(opt => opt.value === form.puesto)}
      placeholder="Seleccione un puesto"
    />
  </div>

  {/* HORARIO */}
  <div className="form-column">
    <h3>HORARIO</h3>

<label>DÍAS:
  <Select
    options={horarios.map(h => ({
      value: h.id,
      label: h.denominativo
    }))}
    onChange={selected =>
      setForm(prev => ({
        ...prev,
        horario: selected?.value || ''
      }))
    }
    value={horarios
      .map(h => ({
        value: h.id,
        label: h.denominativo 
      }))
      .find(opt => opt.value === form.horario)}
    placeholder="Seleccione horario"
    menuPortalTarget={document.body}
  styles={{
    menuPortal: base => ({ ...base, zIndex: 9999 }),
    menu: base => ({ ...base, zIndex: 9999 })
  }}
  />
    
</label>
<label>HORARIO ROTATIVO:
<Select
    options={rotativos.map(h => ({
      value: h,
       label: h 
    }))}
    onChange={selected =>
      setForm(prev => ({
        ...prev,
        rotativo: selected?.value || ''
      }))
    }
    value={rotativos.map(h => ({
        value: h,
       label: h 
      }))
      .find(opt => opt.value === form.rotativo)}
    placeholder="Seleccione horario"
    menuPortalTarget={document.body}
  styles={{
    menuPortal: base => ({ ...base, zIndex: 9999 }),
    menu: base => ({ ...base, zIndex: 9999 })
  }}
  />
</label>


  </div>

  <button type="button" className="btn"   
  onClick={async() => {
      try {
      await guardarEdicionAsignacion(); // Espera a que el POST termine
      await BuscarAsignaciones(); // Luego actualiza la tabla
      QuitarModalEditActualizartablaActualizarFormulario(); // Cierra el modal
    } catch (err) {
      console.error("Error durante la edición");
    }
   
  }}>GUARDAR</button>  
  
  {/*<button type="button" className="btn" onClick={handleSaveNewRecord}>Guardar</button>
  <button type="button" className="btn" onClick={() => setShowModalEdit(false)}>
    Cancelar</button>*/}
    <button type="button" className="btn" 

  
  
  
  
  onClick={() => {setShowModalEdit(false);
    setForm({
    mes: '',
    anio: '',
    razon_social: '',
    nombre_comercial: '',
    direccion: '',
    nombre_instalacion: '',
    ciudad: '',
    provincia: '',
    codigo: '',
    nombre_puesto: '',
    nombre: '',
    apellido: '',
    cedula: '',
    hora_ingreso: '',
    fecha_inicio: '',
    fecha_fin: '',
    hora_salida: '',
    tipo: '',
    cliente: '',
    persona: '',
    horario: '',
    puesto: '',
    rotativo: '',
    instalacion: '',
    estado:''
  });

  }
  }
    
    
    
    >
    Cancelar
    </button>
</form>
  </div>
  


    </div>
  </div>

)}
<div className="filtros-container">
      <button className="btn-paleta" onClick={() => setShowPicker(!showPicker)}>
        {showPicker ? <FaPalette /> : <FaPalette />}
      </button>
      <label>AÑO:
        <Select
          className="horario-select"
          options={anio.map(h => ({ value: h, label: h }))}
          onChange={selected => setForm(prev => ({ ...prev, anio: selected?.value || '' }))}
          value={anio.map(h => ({ value: h, label: h })).find(opt => opt.value === form.anio)}
          placeholder="Seleccione año"
        />
      </label>

      <label>MES:
        <Select
          className="horario-select"
          options={mes.map(a => ({ value: a, label: a }))}
          onChange={selected => setForm(prev => ({ ...prev, mes: selected?.value || '' }))}
          value={mes.map(a => ({ value: a, label: a })).find(opt => opt.value === form.mes)}
          placeholder="Seleccione mes"
          menuPortalTarget={document.body}
        />
      </label>

      <button className="btn-buscar"  onClick={BuscarAsignaciones} ><FaSearch /></button>

      {showPicker && (
        <SketchPicker
          color={selectedColor}
          onChange={(c) => setSelectedColor(c.hex)}
        />
      )}
</div>
      <DragDropContext onDragEnd={onDragEnd}>
      <div className="agruparBoton">
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '10px' }}>
            <button className="btn btn-warning" onClick={() => setShowModal(true)} style={{
              backgroundColor: '#0c2f5a',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '18px'
            }}>
              ＋
            </button>
        </div>


        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '10px'  }}>
            <button className="btn btn-warning" onClick={() => pdf()} style={{
              backgroundColor: '#f10b1eff',
              color: 'white',
              border: 'none',
            
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '18px'
            }}>
              <FontAwesomeIcon icon={faFilePdf} />
            </button>
        
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '10px'  }}>
              <button className="btn btn-warning mt-2" onClick={() => excel()} style={{
              backgroundColor: '#026907ff',
              color: 'white',
              border: 'none',
              
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '18px'
            }}>
              <FontAwesomeIcon icon={faFileExcel} /> 
            </button>
        </div>



          <div style={{ flex:1, textAlign: 'center' }}>
            <label
              style={{
                color: 'black',
                fontSize: '18px',
                fontWeight: 'bold',
              }}
              >
              {form.mes}
            </label>
          </div>
          
        
      </div>
       <DiasConSemana anio={form.anio} mes={10} />
        <table className="horario-tabla">

          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    style={{
                      border: '1px solid #ccc',
                      backgroundColor: '#eee',
                      padding: '10px',
                      fontSize: 10,
                      position: "sticky",
                      top: 0,
                      zIndex: 2,
                    }}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>


          {/* 👉 filas arrastrables */}
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId="table-rows">
              {(provided) => (
                <tbody ref={provided.innerRef} {...provided.droppableProps}>
                  {table.getRowModel().rows.map((row, index) => (
                    <Draggable key={row.original.id} draggableId={row.original.id} index={index}>
                      {(provided) => (
                        <tr
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          {...provided.dragHandleProps}
                          style={{
                            background: "#fff",
                            borderBottom: "1px solid #ccc",
                            ...provided.draggableProps.style
                          }}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <td
                              key={cell.id}
                              style={{
                                border: '1px solid #ccc',
                                padding: '6px',
                                fontSize: 10,
                              }}
                            >
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </td>
                          ))}
                        </tr>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </tbody>
              )}
            </Droppable>
          </DragDropContext>
        </table>
      </DragDropContext>
    </div>

  );

}









export default Horario;
