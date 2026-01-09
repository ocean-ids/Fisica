/*import React from 'react';

function AsignacionServicio() {
  return <h1>AsignacionServicio</h1>;
}

export default AsignacionServicio;*/

import React, { useState, useEffect } from 'react';
import Select from 'react-select';
import './Asignacion.css';
import Swal from 'sweetalert2';
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>

const provincias = ['ESMERALDAS', 'GUAYAS', 'MANABÍ','SANTA ELENA','LOS RÍOS','EL ORO','CARCHI','IMBABURA','PICHINCHA','COTOPAXI','TUNGURAHUA','CHIMBORAZO','BOLÍVAR','CAÑAR','AZUAY','SUCUMBÍOS','NAPO','ORELLANA','PASTAZA','MORONA CHINCHIPE','GALÁPAGOS'];
const ciudades = ['QUITO', 'GUAYAQUIL', 'MANTA','RIOBAMBA','AMBATO','LATACUNGA','CUENCA', 'SANTO DOMINGO', 'DURÁN', 'MACHALA', 'PORTOVIEJO', 'ESMERALDAS', 'LOJA','IBARRA'];
const horas = ['1', '2', '3','4','5','6','7', '8', '9','10','11','12','13', '14', '15','16','17','18','19', '20', '21','22','23','24'];
const dias = ['L', 'M','X','J', 'V','S','D'];
const rotativos = ['3-3-1', '3-3-2','2-2-2','6-2', '5-2','6-1','2-2-1','1-2-4','2-1-7','3-2-2','4-2-2','2-4-2'];



const Asignacion = () => {
  const [form, setForm] = useState({
    // Cliente
    razon_social: '',
    nombre_comercial: '',
    direccion: '',

    // Instalación
    nombre_instalacion: '',
    ciudad: '',
    provincia: '',

    // Puesto
    nombre_puesto: '',

    // Persona
    nombre: '',
    apellido: '',
    cedula: '',

    // Horario
    hora_ingreso: '',
    hora_salida: '',
    denominativo: '',
    denominativo1: '',
    denominativo2: '',
    rotativo: '',
    mes:'',
    anio:'',

    //asignacion
    fecha_fin:'',
    fecha_inicio:''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

    const [clientes, setClientes] = useState([]); // Lista de razones sociales

    const [instalaciones, setInstalaciones] = useState([]);
    const [personas, setPersonas] = useState([]);
    const [fecha, setFecha] = useState('');
    const [puestos, setPuestos] = useState([]);
    const [horarios, setHorarios] = useState([]);
    

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
    })
})
.then(res => res.json())
.then(data => {
  Swal.fire({
    icon: 'success',
    title: '¡Listo!',
    text: data.message,
  });
})
.catch(err => {
  Swal.fire({
    icon: 'error',
    title: 'Error',
    text: 'Ocurrió un problema al asignar',
  });
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
    }, []);



  return (
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
          </div>
  {/* PERSONA */}
  <div className="form-column">
    <h3>PERSONA</h3>
    <Select
      options={personas.map(p => ({ value: p.id, label:`${p.nombres} ${p.apellidos}` }))}
      onChange={selected => setForm(prev => ({ ...prev, persona: selected?.value || '' }))}
      value={personas
        .map(p => ({ value: p.id, label: p.nombres }))
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

  <button type="button" className="btn" onClick={Asignar}>Asignar</button>
</form>
  </div>
  );
};

  
export default Asignacion;
